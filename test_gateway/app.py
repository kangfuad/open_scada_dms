#!/usr/bin/env python3

import socket
import json
import subprocess
import time
import sys
import os
import logging

import libiec60870server
import lib60870
import configparser

hosts_info = {}
async_msg = []
async_rpt = {}
INTERVAL = 2

def read_value(id):
  logger.debug("read value:" + str(id)  )
  if id == config['measuredvaluescaled'][100]:
    readvaluecallback(id,{"value":"0"})
    return 0
  elif id == config['measuredvaluescaled'][101]:
    readvaluecallback(id,{"value":"1"})
    return 0
  elif id == config['measuredvaluescaled'][102]:
    readvaluecallback(id,{"value":"1"})
    return 0
  elif id == config['doublepointinformation'][300]:
    readvaluecallback(id,{"value":str(value)})
    return 0
  elif id == config['doublepointinformation'][301]:
    readvaluecallback(id,{"value":str(value)})
    return 0
  logger.error("read value error:" + str(id)  )  
  return -1 #client.ReadValue(id)


def write_value(id, value):
  logger.info("write value:" + str(value) + ", element:" + str(id) )
  if id == config['doublepointcommand'][6000]:
    readvaluecallback(id,{"value":str(value)})
    return retValue, "no error"
  elif id == config['doublepointcommand'][6001]:
    readvaluecallback(id,{"value":str(value)})
    return retValue, "no error"
  else:
    return retValue, "general error"


def operate(id, value):
  logger.debug("operate:" + str(id) + " v:" + str(value)  )
  readvaluecallback(id,{"value":str(value)})
  return True #send event oper



def select(id, value):
  logger.debug("select:" + str(id)  )
  return True 


def cancel(id):
  logger.debug("cancel:" + str(id)  )
  return  True 


def register_datapoint(id):
  logger.debug("register datapoint:" + str(id) )
  #client.registerReadValue(str(id))


def register_datapoint_finished():
  return



# callbacks from libiec61850client
# called by client.poll
def readvaluecallback(key,data):
  global iec104_server
  global config
  logger.debug("callback: %s - %s" % (key,data))
  for item_type in config:
    for ioa in config[item_type]:
      if config[item_type][ioa] == key:
          iec104_server.update_ioa(int(ioa), data['value'])
          return
  print("could not find IOA for key:" + key)

# callback commandtermination
def cmdTerm_cb(msg):
  async_msg.append(msg)

# callback report
def Rpt_cb(key, value):
  async_rpt[key] = value
  readvaluecallback(key,value)


def read_60870_callback(ioa, ioa_data, iec104server):
  global config
  print("read callback called from lib60870")
  for item_type in config:
    if ioa in config[item_type]:
      return read_value(config[item_type][ioa])

  return -1


def command_60870_callback(ioa, ioa_data, iec104server, select_value):
  print("operate callback called from lib60870")
  for item_type in config:
    if ioa in config[item_type]:
      if select_value == True:
        return select(config[item_type][ioa],  ioa_data['data'])
      else:
        return operate(config[item_type][ioa],  ioa_data['data'])

  return -1


if __name__ == '__main__':
  logger = logging.getLogger('gateway')
  logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
    level=logging.INFO)

  config = configparser.ConfigParser()
  config.optionxform = str # to retain case sentistivy

  if len(sys.argv) > 1:
    config.read(sys.argv[1])
  else:
    config.read('config.local.ini')


  logger.info("started")

  iec104_server = libiec60870server.IEC60870_5_104_server()
  iec104_server.start()

  #REGISTER ALL IOA's and associated IEC61850 datapoints
  if 'measuredvaluescaled' in config:
    for item in config['measuredvaluescaled']:
      #create 104 data for GI
      if iec104_server.add_ioa(int(item), lib60870.MeasuredValueScaled,0,read_60870_callback,True) == 0:
        register_datapoint(config['measuredvaluescaled'][item])
      else:
        logger.error("duplicate IOA:" + item + ", IOA not added to list")
        continue

  if 'singlepointinformation' in config:
    for item in config['singlepointinformation']:
      #create 104 data for GI
      if iec104_server.add_ioa(int(item), lib60870.SinglePointInformation,0,read_60870_callback,True) == 0:
        register_datapoint(config['singlepointinformation'][item])
      else:
        logger.error("duplicate IOA:" + item + ", IOA not added to list")
        continue

  if 'doublepointinformation' in config:
    for item in config['doublepointinformation']:
      #create 104 data for GI
      if iec104_server.add_ioa(int(item), lib60870.DoublePointInformation,0,read_60870_callback,True) == 0:
        register_datapoint(config['doublepointinformation'][item])
      else:
        logger.error("duplicate IOA:" + item + ", IOA not added to list")
        continue
    register_datapoint_finished()

  if 'singlepointcommand' in config:
    for item in config['singlepointcommand']:
      #create 104 data for GI
      if iec104_server.add_ioa(int(item), lib60870.SingleCommand,0,command_60870_callback,False) == 0:
        print("SingleCommand registered")
      else:
        logger.error("duplicate IOA:" + item + ", IOA not added to list")
        continue

  if 'doublepointcommand' in config:
    for item in config['doublepointcommand']:
      #create 104 data for GI
      if iec104_server.add_ioa(int(item), lib60870.DoubleCommand,0,command_60870_callback,False) == 0:
        print("DoubleCommand registered")
      else:
        logger.error("duplicate IOA:" + item + ", IOA not added to list")
        continue


  val1 = 147
  val2 = 41
  val3 = 200
  while True:
    time.sleep(INTERVAL)
    logger.debug("values polled")
    readvaluecallback(config['measuredvaluescaled'][100],{"value":str(val1)})
    readvaluecallback(config['measuredvaluescaled'][101],{"value":str(val2)})
    readvaluecallback(config['measuredvaluescaled'][102],{"value":str(val3)})
    val1 += 1
    val2 += 1
    val3 += 1
    if val1 == 200:
      val1 = 147
      val2 = 41
      val3 = 200
    for key in list(async_rpt):
      val = async_rpt.pop(key)
      logger.debug("%s updated via report" % key)


