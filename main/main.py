from lib2to3.pgen2 import driver
import multiprocessing
import cantools
import can
import pyaudio
import time
import sys
import pandas as pd
import os
import configparser

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from playsound import playsound

def main(save_path, version, driver_list):
    from receive_data import receive_CAN, receive_video, visualize_video, receive_audio, WindowClass
    from check_status import check_driving_cycle, check_velocity, check_driver, check_odometer, check_intention

    ###  CAN setting  ###
    CAN_basePath = os.path.join(save_path, 'dbc')
    P_db = cantools.database.load_file(os.path.join(CAN_basePath, '[DBC filename here].dbc'))
    C_db = cantools.database.load_file(os.path.join(CAN_basePath, '[DBC filename here].dbc'))
    can_bus = can.interface.Bus('can0', bustype='socketcan')
    #####################


    ### Video setting ###
    frontView = True
    sideView = True
    #####################


    ### Audio setting ###
    FORMAT = pyaudio.paInt16
    RATE = 44100
    CHANNELS = 1
    CHUNK = 1024
    #####################

    ### Driving cycle check ###
    check_driving_cycle(P_db, can_bus)
    time.sleep(0.5)


    ### Velocity status check ###
    check_velocity(P_db, can_bus)
    time.sleep(0.5)


    ### DRIVER CHECK ###
    DRIVER_NAME = check_driver(driver_list)


    ### START ODOMETRY CHECK ###
    START_ODO = check_odometer(C_db, can_bus)

    ### DATASET path setting ###
    DATASET_PATH = save_path
    if not os.path.isdir(DATASET_PATH + DRIVER_NAME):
        os.mkdir(DATASET_PATH + DRIVER_NAME)
    DATASET_PATH += (DRIVER_NAME + "/")

    if not os.path.isdir(DATASET_PATH + START_ODO):
        os.mkdir(DATASET_PATH + START_ODO)
    DATASET_PATH += START_ODO
    #####################


    ### Multi-process setting ###
    procs = []
    stop_event = multiprocessing.Event()
    send_conn, recv_conn = multiprocessing.Pipe()

    data_names = ['CAN', 'audio', 'video'] # 'video_visaulizer'
    proc_functions = [receive_CAN, receive_audio, receive_video] # visualize_video
    func_args = {'CAN': (P_db, C_db, can_bus),
                'video': (frontView, sideView, send_conn),
                'audio': (FORMAT, RATE, CHANNELS, CHUNK),
                # 'video_visual': (recv_conn),
                }

    #####################

    ### Driver's intention check ###
    check_intention()

    #####################

    print("[INFO] Main thread started.")

    ### Process generation ###
    for d_name, proc_func in zip(data_names, proc_functions):
        proc = multiprocessing.Process(target=proc_func, args=(d_name, DATASET_PATH, *func_args[d_name], stop_event))
        procs.append(proc)

    for proc in procs:
        proc.start()

    time.sleep(4)

    playsound("../HMI/in.wav")
    myWindow = WindowClass(DRIVER_NAME, DATASET_PATH)
    myWindow.show()


    ### Process terminate ###
    terminate_signal = input("[REQUEST] Press 'Enter' if you want to terminate every processes.\n\n")
    while terminate_signal != '':
        print("[REQUEST] Invalid input! Press 'Enter'")
        terminate_signal = input()

    QCoreApplication.instance().quit
    stop_event.set()

    ### thread terminate double check ###
    for proc in procs:
        proc.join()


    ### Velocity status check ###
    check_velocity(P_db, can_bus)
    time.sleep(0.5)


    ### END ODOMETRY CHECK ###
    END_ODO = check_odometer(C_db, can_bus)
    odo_df = pd.DataFrame([(START_ODO, END_ODO, int(END_ODO) - int(START_ODO), version)], columns=["START", "END", "TOTAL", "VERSION"])
    odo_df.to_csv(f"{DATASET_PATH}/START_END_TOTAL_{int(END_ODO) - int(START_ODO)}km.csv")


    print("[INFO] Main process finished.")

    #####################


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('./config.ini')


    VERSION = config['VERSION']['version']
    SAVE_PATH = config['PATH']['SAVE_PATH']

    DRIVER_LIST = eval(config['DRIVER']['driver_list'])

    app = QApplication(sys.argv)
    main(SAVE_PATH, VERSION, DRIVER_LIST)
