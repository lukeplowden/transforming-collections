from time import sleep
import pandas as pd

import data_processor
import semantic_init
import semantic_client
import serial_com
import ding
import gif_player as gp

import threading
import queue

NUMBER_OF_VECTORS = 4
CSV_PATH = '/Users/erika/Documents/GitHub/transforming-collections/installation-application/data/system-dataset-gif-test.csv'
PURE_DATA_PATH = '/Users/erika/Documents/GitHub/data-sonification/semantic_synth(with-effects).pd'
EMBEDDINGS_PATH = '/Users/erika/Documents/GitHub/transforming-collections/data/input/tate_wellcome_SEA_text_embeddings.npy'
LED_MATRIX_PATH = '/dev/tty.usbmodem2101'
ARUDUINO_PATH = '/dev/tty.usbmodem2201'
JSON_PATH = '/Users/erika/Documents/GitHub/transforming-collections/installation-application/data/country_tracks.json'
DELAY = 5

class MainProgram: 
    def __init__(self, CSV_path, num_vectors, pure_data_path, embeddings_path, led_matrix_path, arduino_path, json_path, delay): 
        try:  
            self.delay = delay
            self.positive_client = semantic_client.SemanticClient("127.0.0.1", 9000)
            self.negative_client = semantic_client.SemanticClient("127.0.0.1", 10000)
            self.semantic_init = semantic_init.SemanticModel(pure_data_path, embeddings_path, num_vectors)
            self.data_processor = data_processor.DataProcessor(CSV_path, self.semantic_init)
            self.LED_matrix = serial_com.SerialCommunication(led_matrix_path)
            self.LED_matrix.connect_serial()
            self.arduino = serial_com.SerialCommunication(arduino_path)
            self.arduino.connect_serial()
            self.ding_model = ding.DingModel(self.arduino, json_path)
        except Exception as e:
            print(f'Error initialising main program! {e}')

    def semantic_model(self, label, vectors):
        if label == 1:
            self.positive_client.send_vectors("/positve", vectors)
        else:
            self.negative_client.send_vectors("/negative", vectors)

    def gif_player(self, gifs):
        for i in range(64):
            if gifs == f"gif-{i}":
                print(f"Found gif-{i}")

    def cleanup(self):
        self.semantic_init.pure_data.terminate()
        self.LED_matrix.close_serial()
        self.arduino.close_serial()

        self.queue = queue.Queue()
        self.gif_player = gp.GifPlayer("./data/gifs", self.queue)
        self.gif_player_thread = threading.Thread(target=self.gif_player.run)
        self.gif_player_thread.start()
        
    def run(self):
        try:
            while True:
                try:
                    row = self.data_processor.get_random_row()
                    vectors = [float(value) for value in row['Vectors']]
                    print(f"Processing index: {row.name}, Countries: {row['Countries']}, Keywords: {row['Keywords']}  Label and vectors: {[row['Label']] +  list(row['Vectors'])}")

                    if pd.notnull(row['Keywords']): self.LED_matrix.send_serial(row['Keywords'])
            
                    self.gif_player(row['Gifs'])

                    self.semantic_model(row['Label'], vectors)

                    if isinstance(row['Countries'], list) and len(row['Countries']) > 0: self.ding_model.run(row['Countries'])

                    sleep(self.delay) 
                except Exception as e:
                    print(f"Error processing row: {e}")
        except KeyboardInterrupt:
            print('user ending program!')
        except Exception as e:
            print(f'Error running main loop: {e}')
        finally:
            self.cleanup()

            
        while True:
            if not self.queue.empty():
                message = self.queue.get()
                if message == "terminate":
                    self.gif_player.terminate()
            self.gif_player.impl_poll_events()
            row = self.data_processor.get_random_row()
            print(f"Processing index: {row.name}, Countries: {row['Countries']}, Keywords: {row['Keywords']}") #, Label and vectors: {[row['Label']] +  list(row['Vectors'])}
            
            # this is just for testing, but I've added about 64 indexes with gifs
            # for i in range(64):
            #     if row['Gifs'] == f"gif-{i}":
            #         print(f"Found gif-{i}")
            #         self.queue.put(f"gif-{i}")

            # sleep(0.1) # you can change this, but in the actual running of the system there will be around 5 - 10 seconds of delay whilst the midi file is played

if __name__ == "__main__":
    try: 
        main_program = MainProgram(CSV_PATH, NUMBER_OF_VECTORS, PURE_DATA_PATH, EMBEDDINGS_PATH, LED_MATRIX_PATH, ARUDUINO_PATH, JSON_PATH ,DELAY)
        main_program.run()
    except Exception as e:
        print(f'Error running main program: {e}')
