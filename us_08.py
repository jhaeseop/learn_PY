import sys
import asyncio
import pandas as pd
import sqlite3

from PyQt5 import uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from PyQt5.QtSerialPort import QSerialPort
from PyQt5.QtSerialPort import QSerialPortInfo
from PyQt5.QtGui import QCloseEvent

from typing import Iterator, Tuple
from serial import Serial
from serial.tools.list_ports import comports

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

form_class = uic.loadUiType("us_08_main.ui")[0]

class WindowClass(QMainWindow, form_class):

    global saved_com

    saved_com = ['COM8', 9600]
    seri = Serial()
    seri.close()
    def __init__(self):
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.fig = plt.Figure()
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.vbox = QVBoxLayout(self.widget)
        self.vbox.addWidget(self.canvas)

        self.setLayout(self.vbox)
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.statusBar().showMessage('연결 포트 : ' + saved_com[0])

        self.btn_measure.clicked.connect(self.dataDraw)
        self.actionSave.triggered.connect(self.save_to_csv)
        self.actionSave_SQL.triggered.connect(self.save_to_sql)
        self.actionSave_Excel.triggered.connect(self.save_to_excel)

        self.actionCOM_Setting.triggered.connect(Serial_Controller)

        self.show()

    def dataDraw(self):
        self.ax.clear()
        self.x = []
        self.y = []
        print('saved_com[0]: ', saved_com[0], type(saved_com[0]))
        print('saved_com[1]: ', saved_com[1], type(saved_com[1]))
        if self.seri.is_open:
            self.seri.close()
        try:
            self.seri = Serial(port=saved_com[0], baudrate=saved_com[1], timeout=0.1)
            print('pass[07]')
        except:
            print('포트를 찾을 수 없습니다.\n')
            self.statusBar().showMessage('포트를 찾을 수 없습니다. 연결상태를 확인해 주세요')
        else:
            if self.seri.is_open:
                self.seri.close()
                print('pass[08]')
            print('pass[09]')
            self.seri.open()
            self.statusBar().showMessage('연결 포트 : ' + saved_com[0])
            self.timer = QTimer()
            self.timer.setInterval(100)
            self.timer.timeout.connect(self.get_data)
            self.timer.start()
            self.btn_stop.clicked.connect(self.timer_stop)

    def timer_stop(self):
        self.timer.stop()
        self.statusBar().showMessage('측정 완료 : ' + saved_com[0])

    def get_data(self):
        value = 0.0
        num = 0
        val = []

        while num < 1:
            msg = self.seri.readline()
            print(msg)
            msg_str = str(msg)
            if msg_str[0: 3] == "b'[":
                value = float(msg_str[3: 8])
                if value and value != 999.0:
                    num += 1

        if len(self.x) == 0:
            self.x = [0]
            self.y = [value]
        else:
            self.x.append(self.x[-1] + 1)
            self.y.append(value)

        self.update_plot()

    def update_plot(self):
        X = self.x[-1:]
        Y = self.y[-1:]
        self.ax.plot(self.x, self.y, 'r-')
        self.canvas.draw()
        text = str(X) + ' : ' + str(Y)
        self.plainTextEdit.appendPlainText(text)

    def save_to_csv(self):
        y_data = pd.DataFrame(self.y)
        y_data.to_csv('./ref_py_files/save_data/csv/data.csv')

    def save_to_sql(self):
        y_data = pd.DataFrame(self.y)
        con = sqlite3.connect('./ref_py_files/save_data/sql/data.db')
        y_data.to_sql('table1', con, if_exists='replace', index=False)  # if_exists=['append','fail']
        con.close()

    def save_to_excel(self):
        y_data = pd.DataFrame(self.y)
        y_data.to_excel('./ref_py_files/save_data/excel/data.xlsx')



form_class_serial = uic.loadUiType('us_08_com.ui')[0]

class Serial_Controller(QWidget, form_class_serial):

    global saved_com
    curr_port = ''
    curr_baud = 0
    available_ports = []
    ser_con = QSerialPort()

    def __init__(self):
        QWidget.__init__(self)
        self.setupUi(self)

        # 많이 사용하는 옵션을 미리 지정해 둔다. baudrate=9600, databits=8
        self.cb_baud_rate.setCurrentIndex(3)
        self.cb_data_bits.setCurrentIndex(3)
        print('pass[00]  ')
        self.cb_port.insertItems(0, self.available_ports)
        print('pass[01]  ')
        self.btn_com_search.clicked.connect(self._search_port)
        self.btn_com_connect.clicked.connect(self.slot_clicked_connect_button)
        print('pass[02]  ')

        test_data = bytes([0x02]) + bytes("TEST DATA", "utf-8") + bytes([0x03])
        self.btn_com_send.clicked.connect(lambda: self.write_data(test_data))
        self.btn_com_receive.clicked.connect(self.receive_data)

        print('pass[03]  ')
        if self.available_ports == []:
            self.update_com_ports()
        if self.ser_con.isOpen():
            self.btn_com_connect.setText('Disconnect')
        else:
            self.btn_com_connect.setText('Connect')
        print('pass[04]  ')
        self._load_settings()
        self.cb_port.setItemText(0, saved_com[0])

        self.show()


    def _load_settings(self):
        """Load settings on startup."""
        # port name
        print('pass 170', saved_com)
        if saved_com[0] == '':
            self.curr_port = self.cb_port.currentText()
            self.curr_baud = int(self.cb_baud_rate.currentText())
        else:
            self.curr_port = saved_com[0]
            self.curr_baud = saved_com[1]
        print('pass 177', saved_com)
        # last message

    def show_error_message(self, msg: str) -> None:
        """Show a Message Box with the error message."""
        QMessageBox.critical(self, QApplication.applicationName(), str(msg))

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle Close event of the Widget."""
        self._save_settings()

    def _save_settings(self):
        saved_com[0] = self.cb_port.currentText()
        saved_com[1] = int(self.cb_baud_rate.currentText())
        print('saved_com : ', saved_com)

    def update_com_ports(self) -> None:
        """Update COM Port list in GUI."""
        ports = comports()
        for p in ports:
            port = p.device
            print('name: ', port, 'type:  ', type(port))
            self.cb_port.addItem(port)

    #@pyqtSlot(QByteArray, name="readData")
    def receive_data(self):
        com_data = self.dataDraw.seri.readline()
        if com_data != b'':
            text = str(com_data)
            self.textEdit.insertPlainText(str('port_name: ' + self.cb_port.currentText()) + text)

    @pyqtSlot(name="clickedConnectButton")
    def slot_clicked_connect_button(self):
        if self.dataDraw.seri.is_open:
            self.disconnect_serial()
            self.btn_com_connect.setText('Connect')
        else:
            self.connect_serial()
            self.btn_com_connect.setText('Disconnect')

    def _search_port(self):
        # 시리얼 상수 값들을 위젯에 채운다
        self.cb_port.clear()
        self.available_ports = []
        print(self.available_ports, '  [S1]')
        self.available_ports = self._get_available_port()
        print('available_ports : ', self.available_ports, type(self.available_ports))
        self.lbl_port.setText("Available Port")
        self.cb_port.insertItems(0, self.available_ports)


    @staticmethod
    def get_port_path():
        """
        현재플래폼에 맞게 경로 또는 지정어를 반환
        :return:
        """
        return {"linux": '/dev/ttyS', "win32": 'COM'}[sys.platform]

    def _get_available_port(self):
        """
        개의 포트를 열고 닫으면서 사용가능한 포트를 찾아서 반환
        :return:
        """
        ports = []
        port_path = self.get_port_path()
        for number in range(10):
            port_name = port_path + str(number)
            if not self._open(port_name):
                continue
            ports.append(port_name)
            self.ser_con.close()
        print(ports, ' [03]  ', type(ports))
        return ports

    def _open(self, port_name, baudrate=QSerialPort.Baud9600, data_bits=QSerialPort.Data8,
              flow_control=QSerialPort.NoFlowControl, parity=QSerialPort.NoParity, stop_bits=QSerialPort.OneStop):
        """
        인자값으로 받은 시리얼 접속 정보를 이용하여 해당 포트를 연결한다.
        :param port_name:
        :param baudrate:
        :param data_bits:
        :param flow_control:
        :param parity:
        :param stop_bits:
        :return: bool
        """
        info = QSerialPortInfo(port_name)
        self.ser_con.setPort(info)
        self.ser_con.setBaudRate(baudrate)
        self.ser_con.setDataBits(data_bits)
        self.ser_con.setFlowControl(flow_control)
        self.ser_con.setParity(parity)
        self.ser_con.setStopBits(stop_bits)
        return self.ser_con.open(QIODevice.ReadWrite)

    def connect_serial(self):
        print('serial open')
        self.ser_con.open()

    def disconnect_serial(self):
        print('serial close')
        self.ser_con.close()

    @pyqtSlot(bytes, name="writeData")
    def write_data(self, data):
        #self.ser_con.writeData(data)
        pass


if __name__ == "__main__" :
    app = QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.show()
    app.exec_()
