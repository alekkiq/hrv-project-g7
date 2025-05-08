from utils import average
from piotimer import Piotimer
from fifo import Fifo
import time
import math

from components.Sensor import SensorFifo
from utils import wait_for_press, save_json, average, stddev, convert_iso_epoch

class BaseMeasurement:
    MIN_BPM = 30
    MAX_BPM = 220
    SAMPLING_RATE = 250
    MIN_PPI_COUNT = 3
    
    """Parent class for measurement classes. contains mutual methods needed for each other measurement class"""
    def __init__(self, display, switch, fifo_size):
        self.display = display
        self.switch = switch
        self.fifo = SensorFifo(fifo_size)
        self.timer = Piotimer(mode = Piotimer.PERIODIC, period = 4, callback = self.fifo.handler)
    
    def get_peaks(self, samples):
        peaks = []
        threshold = average(samples) + (max(samples) - min(samples)) / 5

        for i in range(len(samples) - 1):
            if samples[i] <= threshold <= samples[i + 1]:
                peaks.append(i + 1)

        return peaks

    def get_ppi(self, peaks):    
        # these might need some tweaking still
        ppi_threshold_min = 150
        ppi_threshold_max = 2000

        output = []

        for i in range(len(peaks) - 1):
            ppi = (peaks[i + 1] - peaks[i]) * 4

            if ppi_threshold_min < ppi < ppi_threshold_max:
                output.append(ppi)

        return output

class LiveHRMeasurement(BaseMeasurement):
    """Measurement class for live heart rate measurement"""
    MIN_NORM_PPI_COUNT = 1
    NORM_PPI_TOLERANCE_MS = 250
    BPM_UPDATE_INTERVAL_MS = 5000
    DISPLAY_REFRESH_INTERVAL_MS = 500
    SAMPLE_SIZE = 1250 # 250Hz * 5s

    def collect_samples(self, samples):
        while self.fifo.has_data():
            try:
                samples.append(self.fifo.get())
            except Exception as e:
                print(f"Fifo get error: {e}")
        if len(samples) > self.SAMPLE_SIZE:
            del samples[:-self.SAMPLE_SIZE]  # Keep only latest samples

    def should_update_bpm(self, now, last_update, samples):
        return (
            len(samples) >= self.SAMPLE_SIZE and
            time.ticks_diff(now, last_update) >= self.BPM_UPDATE_INTERVAL_MS
        )

    def update_bpm(self, samples, ppi):
        peaks = self.get_peaks(samples)
        new_ppi = self.get_ppi(peaks)
        samples.clear()
        ppi.extend(new_ppi)

        if len(ppi) > self.MIN_PPI_COUNT:
            peak_avg = average(ppi)
            norm_ppi = [
                i for i in ppi
                if (peak_avg - self.NORM_PPI_TOLERANCE_MS) < i < (peak_avg + self.NORM_PPI_TOLERANCE_MS)
            ]
            if norm_ppi:
                avg_ppi = average(norm_ppi)
                bpm = round(60000 / avg_ppi)
                if self.MIN_BPM <= bpm <= self.MAX_BPM:
                    return bpm, ppi[-5:]

        return 0, ppi

    def display_heart_rate(self, bpm):
        self.display.centered_texts([
            "Live HR",
            " ",
            f"{bpm} BPM" if bpm else "---",
            " ",
            "Press to stop",
        ])

    def cleanup(self, samples, ppi, final_bpm):
        self.display.centered_texts([
            "Final HR",
            " ",
            f"{final_bpm} BPM" if ppi else "---",
            " ",
            "Press to exit",
        ])
        wait_for_press(self.switch)
        samples.clear()
        ppi.clear()
        
    def run(self):
        ROLLING_WINDOW_SIZE = 100
        GRAPH_REFRESH_INTERVAL_MS = 25
        GRAPH_X_SCALE = 2
        VISIBLE_GRAPH_WIDTH = self.display.width // GRAPH_X_SCALE
        rolling_window = []
        samples = []
        ppi = []
        heart_rate = 0
        
        self.fifo.recording = False
        self.fifo.reset()
        self.fifo.recording = True

        self.display.centered_texts(["Live HR", " ", "Press to start"])
        wait_for_press(self.switch)
        print("Live HR recording started")

        last_bpm_update = last_display_refresh = time.ticks_ms()
        last_graph_refresh = time.ticks_ms()

        try:
            self.display.clear()
            while not self.switch.single_press():
                self.collect_samples(samples)
                
                now = time.ticks_ms()
                
                # draw the ppg
                if time.ticks_diff(now, last_graph_refresh) > GRAPH_REFRESH_INTERVAL_MS and samples:
                    new_val = samples[-1]
                    rolling_window.append(new_val)
                    if len(rolling_window) > VISIBLE_GRAPH_WIDTH:
                        rolling_window.pop(0)

                    min_val = min(rolling_window)
                    max_val = max(rolling_window)

                    self.display.draw_ppg_graph(new_val, min_val, max_val)
                    
                if self.should_update_bpm(now, last_bpm_update, samples):
                    new_hr, ppi = self.update_bpm(samples, ppi)
                    if new_hr:
                        heart_rate = new_hr
                        last_bpm_update = now

                # update heading text
                if time.ticks_diff(now, last_display_refresh) > self.DISPLAY_REFRESH_INTERVAL_MS:
                    self.display.heading("HR", f"{heart_rate} BPM" if heart_rate else "---", clear_only_heading = True)
                    last_display_refresh = now

        finally:
            self.fifo.recording = False
            self.cleanup(samples, ppi, heart_rate)
            print("Live HR recording stopped")
            
class AnalysisMeasurement(BaseMeasurement):
    """More in-depth HRV analysis measurement"""
    DURATION_MS = 30000
    SAMPLE_SIZE = 7500 # 250Hz * 30s
    MIN_PPI_COUNT = 10
    
    def __init__(self, *args, with_kubios = False, mqtt_handler = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.with_kubios = with_kubios
        self.mqtt_handler = mqtt_handler
        self.samples = []
        self.ppi = []
        
        # hard-coded history directory
        self.history_dir = "history"
    
    def collect_samples(self):
        self.samples.clear()
        self.ppi.clear()
        start_time = time.ticks_ms()
        
        self.fifo.recording = False
        self.fifo.reset()
        self.fifo.recording = True

        try:
            while time.ticks_diff(time.ticks_ms(), start_time) < self.DURATION_MS:
                if self.fifo.has_data():
                    self.samples.append(self.fifo.get())

                if self.switch.single_press():
                    print("Early stop requested")
                    break

            peaks = self.get_peaks(self.samples)
            print(f"Detected {len(peaks)} peaks")
            
            self.ppi = self.get_ppi(peaks)
            print(f"Extracted {len(self.ppi)} PPI values")

        except Exception as e:
            print(f"Error during data collection: {e}")

        finally:
            self.fifo.recording = False
            print(f"Total PPI values collected: {len(self.ppi)}")
    
    def mean_ppi(self, ppi_list):
        return int(round(sum(ppi_list) / len(ppi_list)))

    def mean_ppi(self, ppi_list):
        return int(round(sum(ppi_list) / len(ppi_list)))

    def mean_hr(self, mean_ppi):
        return int(round(60000 / mean_ppi))

    def sdnn(self, ppi_list):
        mu = sum(ppi_list) / len(ppi_list)
        var = sum((x - mu) ** 2 for x in ppi_list) / (len(ppi_list) - 1)
        return math.sqrt(var)

    def rmssd(self, ppi_list):
        diffs = [ppi_list[i + 1] - ppi_list[i] for i in range(len(ppi_list) - 1)]
        capped_diffs = [min(abs(d), 250) for d in diffs]
        mean_sq = sum(d ** 2 for d in capped_diffs) / len(capped_diffs)
        return math.sqrt(mean_sq)
    
    def calculate_hrv(self):
        """locally calculates wanted HRV parameters from ppi data"""
        mean_ppi = self.mean_ppi(self.ppi)
        mean_hr = self.mean_hr(mean_ppi)
        sdnn = self.sdnn(self.ppi)
        rmssd = self.rmssd(self.ppi)
        
        return {
            "mean_ppi": mean_ppi,
            "mean_hr": mean_hr,
            "sdnn": sdnn,
            "rmssd": rmssd,
        }
            
    def parse_cubios_data(self, data):
        analysis = data["data"]["analysis"]
        
        wanted_fields = {
            "rmssd": "rmssd_ms",
            "mean_hr": "mean_hr_bpm",
            "sdnn": "sdnn_ms",
            "pns": "pns_index",
            "sns": "sns_index",
            "mean_ppi": "mean_rr_ms",
            # add fields later if needed
        }
        
        result = {
            target_key: analysis[source_key]
            for target_key, source_key in wanted_fields.items()
            if source_key in analysis
        }
        
        return result
    
    def run(self):
        """run the measurement"""
        self.display.centered_texts([
            " ", "Place a finger",
            "on the sensor",
            "and press to",
            "start the scan",
        ])

        wait_for_press(self.switch)
        
        self.display.centered_texts([" ", "Collecting data"])

        try:
            self.collect_samples()
            print(len(self.samples))
        except Exception as e:
            print(f"Error during measurement: {e}")
            self.display.centered_texts([
                " ", "Error occurred!", " ",
                "Press to exit",
            ])

        if len(self.ppi) < self.MIN_PPI_COUNT:
            print(f"Not enough data. PPI length: {len(self.ppi)}")
            self.display.centered_texts([
                " ", "Not enough data.", " ",
                "Try again", " ",
                "Press to exit",
            ])
        else:
            try:
                m_id = int(time.time())
                timestamp = int(time.time())
                analysis_type = "kubios" if self.with_kubios else "local"
            
                if self.with_kubios: # kubios analysis selected
                    
                    kubios_payload = {
                        "id": m_id,
                        "type": "RRI",
                        "data": self.ppi,
                        "analysis": {
                            "type": "readiness"
                        }
                    }
                    
                    self.display.centered_texts([
                        " ", "Waiting for",
                        "Kubios response",
                    ])
                    
                    self.mqtt_handler.publish(
                        topic = "kubios-request",
                        data = kubios_payload
                    )
                    
                    while self.mqtt_handler.get_last_message() == None:
                        self.mqtt_handler.listen()
                        mqtt_data = self.mqtt_handler.get_last_message()
                        time.sleep_ms(25)
                    
                    self.mqtt_handler.reset_last_message()
                    
                    data = self.parse_cubios_data(mqtt_data)
                    data["sns"] = round(data["sns"], 3)
                    data["pns"] = round(data["pns"], 3)
                else: # local analysis selected
                    # m_id = int(time.ticks_ms())
                    data = self.calculate_hrv()
                    data["sns"] = "---"
                    data["pns"] = "---"
                    
                # final cleanup to data
                data = {
                    "id": m_id,
                    "timestamp": timestamp,
                    "type": analysis_type,
                    "mean_ppi": round(data.get('mean_ppi')),
                    "mean_hr": round(data.get('mean_hr')),
                    "sdnn": round(data.get('sdnn')),
                    "rmssd": round(data.get('rmssd')),
                    "sns": data["sns"],
                    "pns": data["pns"],
                }
                
                values_to_display = ["mean_ppi", "mean_hr", "sdnn", "rmssd", "sns", "pns"]
                
                # display the values
                self.display.texts(
                    [f"{key.upper().replace('_', ' ')}: {value}" for key, value in data.items() if key in values_to_display]   
                )
                    
                # save data to json
                save_json(self.history_dir, data)
                print(timestamp)
                # publish to MQTT if handler is present
                if self.mqtt_handler.is_connected:
                    self.mqtt_handler.publish("hr-data", data)
            except Exception as e:
                print(f"Error during HRV analysis: {e}")
                self.display.centered_texts([
                    " ","Analysis error!", " ",
                    "Press to exit",
                ])

        wait_for_press(self.switch)