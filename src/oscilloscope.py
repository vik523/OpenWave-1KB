import numpy as np
from gw_com_1kb import com
from gw_lan import lan
import dso1kb
from PIL import Image
import os

class Oscilloscope():
    def __init__(self) -> None:
        return
    def connect(self) -> bool:
        return False
    def capture(self) -> np.array:
        return

class Oscilloscope_gw(Oscilloscope):
    def __init__(self, port, ch1=True, ch2=False) -> None:
        self.port = port
        self.connected = False
        self.device = None
        self.chanels = [[], []]
        if ch1: self.chanels[0] = 'CH1'
        if ch2: self.chanels[1] = 'CH2'
        self.data = [[], []]
        self.units = [[], []]
        return
    
    def _check_connection(self):
        if self.device.connection_status==1:
            self.connected = True
        else:
            self.connected = False
    
    def connect(self):
        port = self._port_check(self.port)
        #Connecting to a self.device.
        try:
            self.device=dso1kb.Dso(port)
            self._check_connection()
        except:
            self.device=dso1kb.Dso('')

    def _port_check(self, port):
        #Check interface according to config file or command line argument.
        if port == '':
            print('Error: Bad config file (add Port parameter in config)')
            return ''
        #Check ethernet connection(model name not checked)
        sInterface=port.split('\n')[0]
        print('sInterface=',sInterface)
        if(sInterface.count('.') == 3 and sInterface.count(':') == 1): #Got ip address.
            ip_str=sInterface.split(':')
            ip=ip_str[0].split('.')
            if(ip_str[1].isdigit() and ip[0].isdigit() and ip[1].isdigit() and ip[2].isdigit() and ip[3].isdigit()):
                print('ip addr=%s.%s.%s.%s:%s'%(ip[0],ip[1],ip[2],ip[3],ip_str[1]))
                port=lan.connection_test(sInterface)
                if(port != ''):
                    return port
        #Check COM port connection(model name not checked)
        elif('COM' in sInterface):
            if(com.connection_test(sInterface) != ''):
                return sInterface
        elif('ttyACM' in sInterface):
            if 'ttyACM' == sInterface[0:6]:
                sInterface='/dev/'+sInterface
            if(com.connection_test(sInterface) != ''):
                return sInterface
        return com.scanComPort()  #Scan all the USB port.
    
    def capture(self, im=False) -> np.array:
        if im:
            result = self.capture_img() 
        else:
            result = self.capture_raw()
        self.units = self.device.vunit
        return result

    def _capture_raw(self):
        self.device.iWave=[[], []]
        self.device.ch_list=[]
        #Turn on the selected channels.
        if(self.chanels[0] and (self.device.isChannelOn(1)==False)):
            self.device.write(":CHAN1:DISP ON\n")           #Set CH1 on.
        if(self.chanels[1] and (self.device.isChannelOn(2)==False)):
            self.device.write(":CHAN2:DISP ON\n")           #Set CH2 on.
        #Get all the selected channel's raw datas.
        if(self.chanels[0]):
            self.device.getRawData(True, 1)              #Read CH1's raw data from self.device (including header).
            self.data[0] = np.asarray(self.device.convertWaveform(0, 1))
        if(self.chanels[1]):
            self.device.getRawData(True, 2)              #Read CH2's raw data from self.device (including header).
            self.data[1] = np.asarray(self.device.convertWaveform(1, 1))
        return self.data
    
    def _capture_img(self):
        img_type=1   #1 for RLE format, 0 for PNG format.
        if(img_type):
            self.device.write(':DISP:OUTP?\n')                 #Send command to get image from DSO.
        else:
            self.device.write(':DISP:PNGOutput?\n')            #Send command to get image from DSO.
        self.device.getBlockData()
        self.device.ImageDecode(img_type)
        print('Image is ready!')
        return self.device.im
    
    def save_data(self, filename):
        num=len(self.device.ch_list)
        #print num
        for ch in range(num):
            if(self.device.info[ch]==[]):
                print('Failed to save data, raw data information is required!')
                return
        f = open(filename, 'w+')
        item=len(self.device.info[0])
        #Write file header.
        if any(self.device.osname == a for a in ['win','win10']) : 
            f.write('%s,\n' % self.device.info[0][0])
        else :
            f.write('%s,\r\n' % self.device.info[0][0])
        for x in range(1,  23):
            str=''
            for ch in range(num):
                str+=('%s,' % self.device.info[ch][x])
            if any(self.device.osname == a for a in ['win','win10']) : 
                str+='\n'
            else :
                str+='\r\n'
            f.write(str)
        #Write Fast CSV mode only.
        str=''
        for ch in range(num):
            str+='Mode,Fast,'
        if any(self.device.osname == a for a in ['win','win10']) : 
            str+='\n'
        else :
            str+='\r\n'
        f.write(str)

        str=''
        if(num==1):
            str+=('%s,' % self.device.info[0][24])
        else:
            for ch in range(num):
                str+=('%s,,' % self.device.info[ch][24])
        if any(self.device.osname == a for a in ['win','win10']) : 
            str+='\n'
        else :
            str+='\r\n'
        f.write(str)
        #Write raw data.
        item=len(self.device.iWave[0])
        #print item
        tenth=int(item/10)
        n_tenth=tenth-1
        percent=10
        for x in range(item):
            str=''
            if(num==1):
                str+=('%s,' % self.device.iWave[0][x])
            else:
                for ch in range(num):
                    str+=('%s, ,' % self.device.iWave[ch][x])
            if any(self.device.osname == a for a in ['win','win10']) : 
                str+='\n'
            else :
                str+='\r\n'
            f.write(str)
            if(x==n_tenth):
                n_tenth+=tenth
                print('%3d %% Saved\r'%percent),
                percent+=10
        f.close()

    def save_image(self, filename):
        modelname = self.device.model_name
        if(self.device.osname=='pi') and any(modelname == a for a in self.device.sModelTranspose) : #For raspberry pi only.
            img=self.device.im.transpose(Image.FLIP_TOP_BOTTOM)
            img.save(filename)
        else:
            self.device.im.save(filename)
        print('Saved image to %s.'%filename)

    def load_data(self, filename):
        self.device.ch_list=[]
        if(len(filename)<=0):
            return
        if os.path.exists(filename):
            print ('Reading file...')
            count=self.device.readRawDataFile(filename)
        else:
            print('File not found!')
        if self.chanels[0]:
            self.data[0] = self.device.convertWaveform(0, 1)
        elif self.chanels[1]:
            self.data[1] = self.device.convertWaveform(1, 1)
        self.units = self.device.vunit[0:2]
        self.chanels = self.device.ch_list[0:2]
    
    def disconect(self):
        if(self.device.connection_status==1):
            self.device.closeIO()
    
    def __del__(self):
        self.disconect()

if __name__ == '__main__':
    port = ''
    device = Oscilloscope_gw(port)
    try:
        device.connect()
    except:
        pass
    if device.connected:
        device.capture()
    else:
        device.load_data('0000000.CSV')

    import matplotlib.pyplot as plt
    plt.figure()
    plt.plot(device.data[0])
    plt.ylabel("%s Units: %s" % (device.chanels[0],  device.units[0]))
    plt.xlabel("Time (sec)")
    plt.show()
    device.disconect()
    print('Finish')