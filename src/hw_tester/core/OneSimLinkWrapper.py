import sys

import os

import platform

import ctypes

import os

import pathlib

import platform

import time

import datetime as dt

import threading

from enum import IntEnum

from enum import Enum

from collections import namedtuple

from _overlapped import NULL

from ctypes import c_char

import sys

import queue

 

###################################

# Structures and enumerations

###################################

 

class Position:

    def __init__(self,

                latitude = sys.float_info.max,

                longitude = sys.float_info.max,

                heading = sys.float_info.max,

                altitude_sea = sys.float_info.max,

                pitch = sys.float_info.max,

                roll = sys.float_info.max,

                altitude_ground = sys.float_info.max,

                x = sys.float_info.max,

                y = sys.float_info.max,

                z = sys.float_info.max):

        self.latitude = latitude

        self.longitude = longitude

        self.heading = heading

        self.altitude_sea = altitude_sea

        self.altitude_ground = altitude_ground

        self.pitch = pitch

        self.roll = roll

        self.x = x

        self.y = y

        self.z = z

 

class Entity:

    def __init__(self):

        self.full_name = ''

        self.dis = ''

        self.type = ''

        self.entity_id = 0

        self.uniqueId = 0

        self.station = ''

        self.parent = ''

        self.aggregator = ''

        self.active = True

        self.publish = True

        self.is_reflected = False

 

class Element:

    def __init__(self):

        self.name = ''

        self.block_name = ''

        self.description = ''

        self.type = ''

        self.raw_data_type = ''

        self.eng_data_type = ''

        self.base_unit = ''

        self.byte_offset = 0

        self.bit_offset = 0

        self.raw_size_in_bits = 0

        self.eng_size_in_bytes = 0

        self.raw_size_in_bytes = 0

        self.scale = 0.0

        self.scale_offset = 0.0

        self.low_value = 0.0

        self.high_value = 0.0

        self.discretes = dict()

 

class RecordingState:

    def __init__(self):

        self.session_mode = ''

        self.recording_time_ms = 0

 

class ElementNotDefinedException(Exception): pass

class EntityNotDefinedException(Exception): pass

class OneSimLinkConfigurationException(Exception): pass

class InvalidArgumentException(Exception): pass

class InvalidOperationException(Exception): pass

class TimeOutException(Exception) : pass

class ModelMessageSendFailureException(Exception) : pass

 

class KindType(IntEnum):

    KIND_OTHER = 0

    KIND_FRIENDLY = 1

    KIND_OPPOSING = 2

    KIND_NEUTRAL = 3

    KIND_OWNSHIP = 4

    KIND_OWNSHIP_FRIENDLY = 5

    KIND_OWNSHIP_OPPOSING = 6

    KIND_OWNSHIP_NEUTRAL = 7

    KIND_OWNSHIP_RC = 8

 

class SimStateType(IntEnum):

    STATE_OFFLINE = 0

    STATE_RESET = 1

    STATE_STOP = 2

    STATE_FREEZE = 3

    STATE_RUN = 4

    STATE_INIT = 5

    STATE_FIRST_INIT = 6

 

class EventType(IntEnum):

    EVENT_LOCAL = 0

    EVENT_GROUP = 1

 

#ElementFormatType.FORAMT_ENG = 0

class ElementFormatType(IntEnum):

    FORAMT_BIN = 1

    FORAMT_HEX = 2

    FORAMT_OCT = 3

    FORAMT_FLOAT = 4

 

class EntityCommandType(IntEnum):

    CMD_ADD = 0

    CMD_DEL = 1

    CMD_PUBLISH = 2

    CMD_UNPUBLISH = 3

    CMD_RENAME = 4

    CMD_MDL_INIT_DONE = 5

 

class EngType(IntEnum):

    ET_BOOLEAN = 0

    ET_CHAR = 1

    ET_INT8 = 2

    ET_UINT8 = 3

    ET_INT16 = 4

    ET_INT32 = 5

    ET_INT64 = 6

    ET_UINT16 = 7

    ET_UINT32 = 8

    ET_UINT64 = 9

    ET_FLOAT = 10

    ET_DOUBLE = 11

    ET_ENUM = 12

    ET_STRING = 13

 

class RawType(IntEnum):

    RT_SIGNED = 0

    RT_UNSIGNED = 1

    RT_BCD = 2

    RT_FLOAT = 3

    RT_DOUBLE = 4

    RT_STR = 5

    RT_AS6 = 6

    RT_AS7 = 7

 

class ElementRegistrationEventType(IntEnum):

    ELEMENT_UNREGISTERED = 0

    ELEMENT_ATTACHED = 1

    ELEMENT_DETACHED = 2

 

# should only be used internally

class _ErrorType(IntEnum):

    ERROR_NONE = 0

    ERROR_UNDEFINED_ENTITY = 1

    ERROR_INACTIVE_ENTITY = 2

    ERROR_DIS_TYPE_NOT_DEFINED = 3

    ERROR_SAMPLE_TIMEOUT = 4

    ERROR_NOT_SAMPLED = 5

    ERROR_CONFIGURATION = 6

    ERROR_DISABLED_WHILE_INITS = 7

    ERROR_INVALID_ELEMENT = 8

    ERROR_INVALID_ARGUMENTS = 9

    ERROR_INVALID_OP = 10

 

###################################

 

class simTimer():

    _instance = None

    _enable_timer = True

    _scale = 1

    _max_time = sys.float_info.max

 

    @staticmethod

    def get_instance():

        if simTimer._instance is None:

            simTimer()

        instance = simTimer._instance

        return instance

 

    def __init__(self):

        if simTimer._instance is not None:

            raise Exception("Class simTimer is a singleton. use the simTimer.get_instance()")

        else:

            simTimer._instance = self

 

    def enable_timer(self, enable):

        simTimer._enable_timer = enable

 

    def set_timer_scale(self, scale):

        simTimer._scale = scale

 

    def set_timer_max_time(self, max_time):

        simTimer._max_time = max_time

 

    def sleep(self, sleep_time):

        adjusted_sleep_time = (sleep_time * simTimer._scale)

        if adjusted_sleep_time > simTimer._max_time:

            adjusted_sleep_time = simTimer._max_time

        if simTimer._enable_timer is True:

            time.sleep(adjusted_sleep_time)

 

###################################

 

def server_update_thread(name, se):

    minor = se.get_minor_period() / 1000

    while True:

        se.server_update()

        if not simWrapper.best_effort:

            time.sleep(minor)

 

def poll_events_thread(name, se):

    minor = se.get_minor_period() / 1000

    while True:

        se.poll_events()

        if not simWrapper.best_effort:

            time.sleep(minor)

 

class simWrapper():

    _ELEMENT_BUFFER_SIZE=1000

    _instance = None

    thread_started = False

    best_effort = False

 

    @staticmethod

    def get_instance():

        if simWrapper._instance is None:

            simWrapper()

        instance = simWrapper._instance

        if instance._init_ok == True:

            if not simWrapper.thread_started:

                instance._osl_set_to_optimum_affinity()

                instance.server_update()

                instance.__register_element_registration_event_handler()

                _server_update_thread = threading.Thread(target = server_update_thread, args = (1, instance), daemon = True)

                _server_update_thread.start()

                simWrapper.thread_started = True

                simWrapper.events_thread_started = False

                instance.__wait_for_connection(90)

                print('Onesim-link was loaded successfully!')

        return instance

 

    def __init__(self):

        if simWrapper._instance is not None:

            raise Exception("Class simWrapper is a singleton. use the simWrapper.get_instance()")

        else:

            print('Loading onesim-link, please wait!')

            self._initialize_functions()

            # Buffer for results

            self._err = ctypes.c_int()

            self._val = ctypes.create_string_buffer(b'\000' * self._ELEMENT_BUFFER_SIZE)

            self._last_server_update = dt.datetime.now().microsecond / 1000

            simWrapper._instance = self

 

    def _initialize_functions(self):

        self._registered_elements = dict() # dictionary: elementName->registration id

        self._reveresed_registered_elements = dict() # dictionary: registration id->elementName

        self._registered_elements_lock = threading.Lock()

 

        ###################################

        # General

        ###################################

 

        dll_path = os.path.join(os.getcwd(), "OneSimLink.dll")

       

        if not os.path.exists(dll_path):

            # attempt to find at Release folder

            onesimpath = pathlib.Path(os.environ["GESSTPATH"]) / "CurrentProject/API/Python/"

            sys.path.insert(0, str(onesimpath))

            architecture = platform.architecture()[0]

            if architecture == '64bit':

                onesimBinPath = pathlib.Path(os.environ["GESSTPATH"]) / "Bin/Release_x64/"

            else:

                onesimBinPath = pathlib.Path(os.environ["GESSTPATH"]) / "Bin/Release_Win32/"

            os.chdir(onesimBinPath)

            dll_path = os.path.join(os.getcwd(), "OneSimLink.dll")

 

        print("DLL found at {}, attempting to load directly...".format(dll_path))

        ctypes.CDLL(dll_path)   

 

        self._osl_onesim_link_startup = ctypes.cdll.OneSimLink.OneSimLinkStartup

        self._osl_onesim_link_startup.restype = ctypes.c_bool

 

        self._osl_get_error = ctypes.cdll.OneSimLink.GetError

        self._osl_get_error.restype = ctypes.c_char_p

 

        self._osl_server_update = ctypes.cdll.OneSimLink.ServerUpdate

        self._osl_send_pending_requests = ctypes.cdll.OneSimLink.SendPendingRequests

 

        self._osl_set_to_optimum_affinity = ctypes.cdll.OneSimLink.SetToOptimumAffinity

 

        ###################################

        # Entities

        ###################################

 

        self._osl_get_num_of_entities = ctypes.cdll.OneSimLink.GetNumOfEntities

        self._osl_get_num_of_entities.restype = ctypes.c_uint

 

        self._osl_get_entity_name = ctypes.cdll.OneSimLink.GetEntityNameForScripts

        self._osl_get_entity_name.restype = ctypes.c_char_p

 

        self._osl_get_entity_type_name = ctypes.cdll.OneSimLink.GetEntityTypeNameForScripts

        self._osl_get_entity_type_name.restype = ctypes.c_char_p

 

        self._osl_get_entity_attributes = ctypes.cdll.OneSimLink.GetEntityAttributesForScripts

        self._osl_get_entity_attributes.argtypes = [ctypes.c_void_p,

                                                    ctypes.c_uint,

                                                    ctypes.c_void_p,

                                                    ctypes.c_void_p,

                                                    ctypes.c_void_p,

                                                    ctypes.c_void_p,

                                                    ctypes.c_void_p,

                                                    ctypes.c_void_p,

                                                    ctypes.c_void_p]

        self._osl_get_entity_attributes.restype = ctypes.c_bool

 

        self._osl_get_entity_position = ctypes.cdll.OneSimLink.GetEntityPosition

        self._osl_get_entity_position.restype = ctypes.c_bool

 

        self._osl_set_entity_position_request = ctypes.cdll.OneSimLink.SetEntityPositionRequest

        self._osl_set_entity_position_request.argtypes = [ctypes.c_void_p,

                                                            ctypes.c_uint,

                                                            ctypes.c_double,

                                                            ctypes.c_double,

                                                            ctypes.c_double,

                                                            ctypes.c_double,

                                                            ctypes.c_double,

                                                            ctypes.c_double,

                                                            ctypes.c_double]

        self._osl_set_entity_position_request.restype = ctypes.c_bool

 

        self._osl_get_entity_dis_as_string = ctypes.cdll.OneSimLink.GetEntityDisAsString

        self._osl_get_entity_dis_as_string.restype = ctypes.c_char_p

 

        self._osl_get_entity_kind = ctypes.cdll.OneSimLink.GetEntityKind

        self._osl_get_entity_kind.restype = ctypes.c_bool

 

        self._osl_set_entity_kind = ctypes.cdll.OneSimLink.SetEntityKind

        self._osl_set_entity_kind.argtypes = [ctypes.c_char_p, ctypes.c_uint, ctypes.c_int]

        self._osl_set_entity_kind.restype = ctypes.c_bool

 

        self._osl_get_entity_id = ctypes.cdll.OneSimLink.GetEntityIdByName

        self._osl_get_entity_id.argtypes = [ctypes.c_char_p]

        self._osl_get_entity_id.restype = ctypes.c_int

 

        self._osl_get_entity_model_init_done = ctypes.cdll.OneSimLink.GetEntityModelInitDone

        self._osl_get_entity_model_init_done.restype = ctypes.c_bool

 

        self._osl_add_entity_request = ctypes.cdll.OneSimLink.AddEntityRequest

        self._osl_add_entity_request.argtypes = [ctypes.c_void_p,

                                          ctypes.c_char_p,

                                          ctypes.c_char_p,

                                          ctypes.c_bool,

                                          ctypes.c_char_p,

                                          ctypes.c_bool,

                                          ctypes.c_int,

                                          ctypes.c_double,

                                          ctypes.c_double,

                                          ctypes.c_double,

                                          ctypes.c_double,

                                          ctypes.c_double,

                                          ctypes.c_double,

                                          ctypes.c_double,

                                          ctypes.POINTER(ctypes.c_char_p),

                                          ctypes.POINTER(ctypes.c_char_p),

                                          ctypes.c_uint]

        self._osl_add_entity_request.restype = ctypes.c_bool

 

        self._osl_add_entity_with_params_request = ctypes.cdll.OneSimLink.AddEntityWithParamsRequest

        self._osl_add_entity_with_params_request.argtypes = [ctypes.c_void_p,

                                          ctypes.c_char_p,

                                          ctypes.c_char_p,

                                          ctypes.c_bool,

                                          ctypes.c_char_p,

                                          ctypes.c_bool,

                                          ctypes.POINTER(ctypes.c_char_p),

                                          ctypes.POINTER(ctypes.c_char_p),

                                          ctypes.c_uint]

        self._osl_add_entity_with_params_request.restype = ctypes.c_bool

 

        self._osl_duplicate_entity_request = ctypes.cdll.OneSimLink.DuplicateEntityRequest

        self._osl_duplicate_entity_request.argtypes = [ctypes.c_void_p,

                                          ctypes.c_uint,

                                          ctypes.c_char_p,

                                          ctypes.c_double,

                                          ctypes.c_double,

                                          ctypes.c_double,

                                          ctypes.c_bool,

                                          ctypes.POINTER(ctypes.c_char_p),

                                          ctypes.POINTER(ctypes.c_char_p),

                                          ctypes.c_uint,

                                          ctypes.c_bool]

        self._osl_duplicate_entity_request.restype = ctypes.c_bool

 

        self._osl_remove_entity_request = ctypes.cdll.OneSimLink.RemoveEntityRequest

        self._osl_remove_entity_request.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_bool]

        self._osl_remove_entity_request.restype = ctypes.c_bool

 

        self._osl_remove_aggregator_request = ctypes.cdll.OneSimLink.RemoveAggregatorRequest

        self._osl_remove_aggregator_request.argtypes = [ctypes.c_void_p, ctypes.c_uint]

        self._osl_remove_aggregator_request.restype = ctypes.c_bool

 

        self._osl_set_aggregation_request = ctypes.cdll.OneSimLink.SetAggregationRequest

        self._osl_set_aggregation_request.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]

        self._osl_set_aggregation_request.restype = ctypes.c_bool

 

        self.EntitiesFuncType = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_uint, ctypes.c_char_p, ctypes.c_char_p)

        self._osl_set_entities_event_handler = ctypes.cdll.OneSimLink.SetEntitiesEventHandler

        self._osl_set_entities_event_handler.argtypes = [self.EntitiesFuncType]

 

        self.EntitiesAggregationFuncType = ctypes.CFUNCTYPE(None, ctypes.c_uint, ctypes.c_int, ctypes.c_int)

        self._osl_set_entities_aggregation_event_handler = ctypes.cdll.OneSimLink.SetEntitiesAggregationEventHandler

        self._osl_set_entities_aggregation_event_handler.argtypes = [self.EntitiesAggregationFuncType]

 

        self._osl_entity_id_to_unique_id = ctypes.cdll.OneSimLink.EntityIdToUniqueId

        self._osl_entity_id_to_unique_id.argtypes = [ctypes.c_uint]

        self._osl_entity_id_to_unique_id.restype = ctypes.c_int

 

        self._osl_get_platform_name = ctypes.cdll.OneSimLink.GetPlatformName

        self._osl_get_platform_name.argtypes = [ctypes.c_uint]

        self._osl_get_platform_name.restype = ctypes.c_char_p

 

        ###################################

        # Elements

        ###################################

 

        self._osl_get_block_def_id_from_block = ctypes.cdll.OneSimLink.GetBlockDefIdFromBlock

        self._osl_get_block_def_id_from_block.argtypes = [ctypes.c_uint]

        self._osl_get_block_def_id_from_block.restype = ctypes.c_int

 

        self._osl_register_element = ctypes.cdll.OneSimLink.RegisterElement

        self._osl_register_element.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_bool, ctypes.c_bool]

        self._osl_register_element.restype = ctypes.c_int

 

        self._osl_element_sample_request = ctypes.cdll.OneSimLink.ElementSampleRequest

        self._osl_element_sample_request.argtypes = [ctypes.c_uint]

        self._osl_element_sample_request.restype = ctypes.c_bool

 

        self._osl_set_element_value_request_for_scripts = ctypes.cdll.OneSimLink.SetElementValueRequestForScripts

        self._osl_set_element_value_request_for_scripts.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int, ctypes.c_bool, ctypes.c_bool]

        self._osl_set_element_value_request_for_scripts.restype = ctypes.c_bool

 

        self._osl_set_element_unit = ctypes.cdll.OneSimLink.SetElementUnit

        self._osl_set_element_unit.argtypes = [ctypes.c_uint, ctypes.c_char_p]

        self._osl_set_element_unit.restype = ctypes.c_bool

 

        self._osl_element_unapply_request = ctypes.cdll.OneSimLink.ElementUnApplyRequest

        self._osl_element_unapply_request.argtypes = [ctypes.c_uint]

        self._osl_element_unapply_request.restype = ctypes.c_bool

 

        self._osl_is_received_messages_from_rt = ctypes.cdll.OneSimLink.IsReceivedMessagesFromRt

        self._osl_is_received_messages_from_rt.restype = ctypes.c_bool

 

        self._osl_get_element_value_for_scripts = ctypes.cdll.OneSimLink.GetElementValueForScripts

        self._osl_get_element_value_for_scripts.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_uint]

        self._osl_get_element_value_for_scripts.restype = ctypes.c_bool

 

        self._osl_unregister_element = ctypes.cdll.OneSimLink.UnRegisterElement

        self._osl_unregister_element.argtypes = [ctypes.c_uint]

        self._osl_unregister_element.restype = ctypes.c_bool

 

        self._osl_is_element_valid = ctypes.cdll.OneSimLink.IsElementValid

        self._osl_is_element_valid.argtypes = [ctypes.c_uint]

        self._osl_is_element_valid.restype = ctypes.c_bool

 

        self._osl_element_exists_for_script = ctypes.cdll.OneSimLink.ElementExistsForScripts

        self._osl_element_exists_for_script.argtypes = [ctypes.c_char_p]

        self._osl_element_exists_for_script.restype = ctypes.c_bool

 

        self._osl_is_element_sampled = ctypes.cdll.OneSimLink.IsElementSampled

        self._osl_is_element_sampled.argtypes = [ctypes.c_uint]

        self._osl_is_element_sampled.restype = ctypes.c_bool

 

        self._osl_is_element_applied = ctypes.cdll.OneSimLink.IsElementApplied

        self._osl_is_element_applied.argtypes = [ctypes.c_uint]

        self._osl_is_element_applied.restype = ctypes.c_bool

 

        self._osl_get_element_block_def_id = ctypes.cdll.OneSimLink.GetElementBlockDefId

        self._osl_get_element_block_def_id.argtypes = [ctypes.c_uint]

        self._osl_get_element_block_def_id.restype = ctypes.c_int

 

        self._osl_get_element_index_in_block = ctypes.cdll.OneSimLink.GetElementIndexInBlock

        self._osl_get_element_index_in_block.argtypes = [ctypes.c_uint]

        self._osl_get_element_index_in_block.restype = ctypes.c_int

 

        self._osl_unapply_on_exit = ctypes.cdll.OneSimLink.UnapplyOnExit

        self._osl_unapply_on_exit.argtypes = [ctypes.c_bool]

 

        self._osl_get_amount_of_defined_lrus = ctypes.cdll.OneSimLink.GetAmountOfDefinedLrus

        self._osl_get_amount_of_defined_lrus.restype = ctypes.c_uint

 

        self._osl_get_lru_def_name = ctypes.cdll.OneSimLink.GetLruDefName

        self._osl_get_lru_def_name.argtypes = [ctypes.c_uint]

        self._osl_get_lru_def_name.restype = ctypes.c_char_p

 

        self._osl_get_amount_of_block_defs = ctypes.cdll.OneSimLink.GetAmountOfBlockDefs

        self._osl_get_amount_of_block_defs.argtypes = [ctypes.c_uint]

        self._osl_get_amount_of_block_defs.restype = ctypes.c_int

 

        self._osl_get_block_id_by_name = ctypes.cdll.OneSimLink.GetBlockIdByName

        self._osl_get_block_id_by_name.argtypes = [ctypes.c_char_p]

        self._osl_get_block_id_by_name.restype = ctypes.c_int

 

        self._osl_get_block_def_id = ctypes.cdll.OneSimLink.GetBlockDefId

        self._osl_get_block_def_id.argtypes = [ctypes.c_uint, ctypes.c_uint]

        self._osl_get_block_def_id.restype = ctypes.c_int

 

        self._osl_get_block_def_amount_of_elements = ctypes.cdll.OneSimLink.GetBlockDefAmountOfElements

        self._osl_get_block_def_amount_of_elements.argtypes = [ctypes.c_uint]

        self._osl_get_block_def_amount_of_elements.restype = ctypes.c_int

 

        self._osl_get_def_element_name = ctypes.cdll.OneSimLink.GetDefElementName

        self._osl_get_def_element_name.argtypes = [ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_name.restype = ctypes.c_char_p

 

        self._osl_get_block_name = ctypes.cdll.OneSimLink.GetBlockDefName

        self._osl_get_block_name.argtypes = [ctypes.c_uint]

        self._osl_get_block_name.restype = ctypes.c_char_p

 

        self._osl_get_def_element_description = ctypes.cdll.OneSimLink.GetDefElementDescription

        self._osl_get_def_element_description.argtypes = [ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_description.restype = ctypes.c_char_p

 

        self._osl_get_def_element_type = ctypes.cdll.OneSimLink.GetDefElementType

        self._osl_get_def_element_type.argtypes = [ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_type.restype = ctypes.c_char_p

 

        self._osl_get_def_element_eng_type = ctypes.cdll.OneSimLink.GetDefElementEngType

        self._osl_get_def_element_eng_type.argtypes = [ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_eng_type.restype = ctypes.c_int

 

        self._osl_get_def_element_raw_type = ctypes.cdll.OneSimLink.GetDefElementRawType

        self._osl_get_def_element_raw_type.argtypes = [ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_raw_type.restype = ctypes.c_int

 

        self._osl_get_def_element_default_unit = ctypes.cdll.OneSimLink.GetDefElementDefaultUnit

        self._osl_get_def_element_default_unit.argtypes = [ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_default_unit.restype = ctypes.c_char_p

 

        self._osl_get_def_element_byte_offset = ctypes.cdll.OneSimLink.GetDefElementByteOffset

        self._osl_get_def_element_byte_offset.argtypes = [ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_byte_offset.restype = ctypes.c_int

 

        self._osl_get_def_element_bit_offset = ctypes.cdll.OneSimLink.GetDefElementBitOffset

        self._osl_get_def_element_bit_offset.argtypes = [ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_bit_offset.restype = ctypes.c_int

 

        self._osl_get_def_element_raw_size_in_bits = ctypes.cdll.OneSimLink.GetDefElementRawSizeInBits

        self._osl_get_def_element_raw_size_in_bits.argtypes = [ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_raw_size_in_bits.restype = ctypes.c_int

 

        self._osl_get_def_element_eng_size_in_bytes = ctypes.cdll.OneSimLink.GetDefElementEngSizeInBytes

        self._osl_get_def_element_eng_size_in_bytes.argtypes = [ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_eng_size_in_bytes.restype = ctypes.c_int

 

        self._osl_get_def_element_raw_size_in_bytes = ctypes.cdll.OneSimLink.GetDefElementRawSizeInBytes

        self._osl_get_def_element_raw_size_in_bytes.argtypes = [ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_raw_size_in_bytes.restype = ctypes.c_int

 

        self._osl_get_def_element_scale = ctypes.cdll.OneSimLink.GetDefElementScale

        self._osl_get_def_element_scale.argtypes = [ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_scale.restype = ctypes.c_double

 

        self._osl_get_def_element_scale_offset = ctypes.cdll.OneSimLink.GetDefElementScaleOffset

        self._osl_get_def_element_scale_offset.argtypes = [ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_scale_offset.restype = ctypes.c_double

 

        self._osl_get_def_element_amount_of_discretes = ctypes.cdll.OneSimLink.GetDefElementAmountOfDiscretes

        self._osl_get_def_element_amount_of_discretes.argtypes = [ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_amount_of_discretes.restype = ctypes.c_int

 

        self._osl_get_def_element_discrete_key = ctypes.cdll.OneSimLink.GetDefElementDiscreteKey

        self._osl_get_def_element_discrete_key.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_discrete_key.restype = ctypes.c_char_p

 

        self._osl_get_def_element_discrete_value = ctypes.cdll.OneSimLink.GetDefElementDiscreteValue

        self._osl_get_def_element_discrete_value.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_discrete_value.restype = ctypes.c_int

 

        self._osl_get_def_element_range_low_value = ctypes.cdll.OneSimLink.GetDefElementRangeLowValue

        self._osl_get_def_element_range_low_value.argtypes = [ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_range_low_value.restype = ctypes.c_double

 

        self._osl_get_def_element_range_high_value = ctypes.cdll.OneSimLink.GetDefElementRangeHighValue

        self._osl_get_def_element_range_high_value.argtypes = [ctypes.c_uint, ctypes.c_uint]

        self._osl_get_def_element_range_high_value.restype = ctypes.c_double

 

        self.ElementRegistrationFuncType = ctypes.CFUNCTYPE(None, ctypes.c_uint, ctypes.c_int)

        self._osl_set_element_registration_event_handler = ctypes.cdll.OneSimLink.SetElementRegistrationEventHandler

        self._osl_set_element_registration_event_handler.argtypes = [self.ElementRegistrationFuncType]

 

        ###################################

        # SimState

        ###################################

 

        self._osl_set_simstate_request = ctypes.cdll.OneSimLink.SetSimStateRequest

        self._osl_set_simstate_request.argtypes = [ctypes.c_int]

 

        self._osl_get_simengine_time_msec = ctypes.cdll.OneSimLink.GetSimEngineTimeMsec

        self._osl_get_simengine_time_msec.restype = ctypes.c_int

 

        self._osl_get_simstate = ctypes.cdll.OneSimLink.GetSimState

        self._osl_get_simstate.restype = ctypes.c_int

 

        self._osl_get_minor_period = ctypes.cdll.OneSimLink.GetMinorPeriod

        self._osl_get_minor_period.restype = ctypes.c_uint

 

        self.SimStateFuncType = ctypes.CFUNCTYPE(None, ctypes.c_int)

        self._osl_set_simstate_event_handler = ctypes.cdll.OneSimLink.SetSimStateEventHandler

        self._osl_set_simstate_event_handler.argtypes = [self.SimStateFuncType]

 

        ###################################

        # Group and Stations

        ###################################

 

        self._osl_get_amount_of_stations = ctypes.cdll.OneSimLink.GetAmountOfStations

        self._osl_get_amount_of_stations.restype = ctypes.c_uint

 

        self._osl_get_station_name_by_index = ctypes.cdll.OneSimLink.GetStationNameByIndex

        self._osl_get_station_name_by_index.argtypes = [ctypes.c_uint]

        self._osl_get_station_name_by_index.restype = ctypes.c_char_p

 

        self._osl_get_station_name_id_name = ctypes.cdll.OneSimLink.GetStationIdByName

        self._osl_get_station_name_id_name.argtypes = [ctypes.c_char_p]

        self._osl_get_station_name_id_name.restype = ctypes.c_int

 

        self._osl_get_station_name_by_id = ctypes.cdll.OneSimLink.GetStationNameById

        self._osl_get_station_name_by_id.argtypes = [ctypes.c_uint]

        self._osl_get_station_name_by_id.restype = ctypes.c_char_p

 

        self._osl_get_amount_of_stations_in_workgroup = ctypes.cdll.OneSimLink.GetAmountOfStationsInWorkGroup

        self._osl_get_amount_of_stations_in_workgroup.argtypes = [ctypes.c_char_p]

        self._osl_get_amount_of_stations_in_workgroup.restype = ctypes.c_uint

 

        self._osl_get_local_workgroup_name = ctypes.cdll.OneSimLink.GetLocalWorkGroupName

        self._osl_get_local_workgroup_name.restype = ctypes.c_char_p

 

        self._osl_get_station_name_in_workgroup_by_index = ctypes.cdll.OneSimLink.GetWorkGroupStationName

        self._osl_get_station_name_in_workgroup_by_index.argtypes = [ctypes.c_char_p, ctypes.c_uint]

        self._osl_get_station_name_in_workgroup_by_index.restype = ctypes.c_char_p

 

        self._osl_get_own_station_id = ctypes.cdll.OneSimLink.GetOwnStationId

        self._osl_get_own_station_id.restype = ctypes.c_uint

 

        self._osl_get_station_simstate = ctypes.cdll.OneSimLink.GetStationSimState

        self._osl_get_station_simstate.argtypes = [ctypes.c_uint]

        self._osl_get_station_simstate.restype = ctypes.c_int

 

        ###################################

        # Events

        ###################################

 

        self._osl_inject_event_eng_request = ctypes.cdll.OneSimLink.InjectEventEngRequest

        self._osl_inject_event_eng_request.restype = ctypes.c_bool

 

        self._osl_get_event_id = ctypes.cdll.OneSimLink.GetEventId

        self._osl_get_event_id.argtypes = [ctypes.c_char_p]

        self._osl_get_event_id.restype = ctypes.c_int

 

        self._osl_get_event_class_id = ctypes.cdll.OneSimLink.GetEventClassId

        self._osl_get_event_class_id.argtypes = [ctypes.c_char_p]

        self._osl_get_event_class_id.restype = ctypes.c_int

 

        self._osl_poll_events = ctypes.cdll.OneSimLink.PollEvents

 

        self._osl_start_events_monitoring = ctypes.cdll.OneSimLink.StartEventsMonitoring

 

        self._osl_clear_events_filter = ctypes.cdll.OneSimLink.ClearEventsFilter

 

        self._osl_add_events_filter = ctypes.cdll.OneSimLink.AddEventsFilter

        self._osl_add_events_filter.argtypes = [ctypes.c_char_p]

        self._osl_add_events_filter.restype = ctypes.c_bool

 

        self._osl_get_amount_of_event_elements = ctypes.cdll.OneSimLink.GetAmountOfEventElements

        self._osl_get_amount_of_event_elements.argtypes = [ctypes.c_uint]

        self._osl_get_amount_of_event_elements.restype = ctypes.c_int

 

        self._osl_get_event_element_value = ctypes.cdll.OneSimLink.GetEventElementValue

        self._osl_get_event_element_value.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]

        self._osl_get_event_element_value.restype = ctypes.c_char_p

 

        self.SimEngineEventFuncType = ctypes.CFUNCTYPE(None, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint, ctypes.c_char_p, ctypes.c_uint, ctypes.c_char_p, ctypes.c_int, ctypes.c_uint, ctypes.c_int, ctypes.c_void_p, ctypes.c_int)

        self._osl_set_sim_engine_event_handler = ctypes.cdll.OneSimLink.SetSimEngineEventHandler

        self._osl_set_sim_engine_event_handler.argtypes = [self.SimEngineEventFuncType]

 

        self._osl_get_amount_of_events = ctypes.cdll.OneSimLink.GetAmountOfEvents

        self._osl_get_amount_of_events.restype = ctypes.c_uint

 

        self._osl_get_event_name = ctypes.cdll.OneSimLink.GetEventName

        self._osl_get_event_name.argtypes = [ctypes.c_uint]

        self._osl_get_event_name.restype = ctypes.c_char_p

 

        self._osl_get_amount_of_event_classes = ctypes.cdll.OneSimLink.GetAmountOfEventClasses

        self._osl_get_amount_of_event_classes.restype = ctypes.c_uint

 

        self._osl_get_event_class_name = ctypes.cdll.OneSimLink.GetEventClassName

        self._osl_get_event_class_name.argtypes = [ctypes.c_uint]

        self._osl_get_event_class_name.restype = ctypes.c_char_p

 

        ###################################

        # Recorder

        ###################################

 

        self._osl_start_recording_request = ctypes.cdll.OneSimLink.StartRecordingRequest

        self._osl_start_recording_request.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint]

        self._osl_start_recording_request.restype = ctypes.c_bool

 

        self._osl_start_playback_request = ctypes.cdll.OneSimLink.StartPlaybackRequest

        self._osl_start_playback_request.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

        self._osl_start_playback_request.restype = ctypes.c_bool

 

        self._osl_jump_to_time_request = ctypes.cdll.OneSimLink.JumpToTimeRequest

        self._osl_jump_to_time_request.argtypes = [ctypes.c_void_p, ctypes.c_longlong]

        self._osl_jump_to_time_request.restype = ctypes.c_bool

 

        self._osl_play_forward_request = ctypes.cdll.OneSimLink.PlayForwardRequest

        self._osl_play_forward_request.argtypes = [ctypes.c_void_p, ctypes.c_float]

        self._osl_play_forward_request.restype = ctypes.c_bool

 

        self._osl_play_backward_request = ctypes.cdll.OneSimLink.PlayBackwardRequest

        self._osl_play_backward_request.argtypes = [ctypes.c_void_p, ctypes.c_float]

        self._osl_play_backward_request.restype = ctypes.c_bool

 

        self._osl_close_session_request = ctypes.cdll.OneSimLink.CloseSessionRequest

        self._osl_close_session_request.argtypes = [ctypes.c_void_p]

        self._osl_close_session_request.restype = ctypes.c_bool

 

        self._osl_save_snappoint_request = ctypes.cdll.OneSimLink.SaveSnapPointRequest

        self._osl_save_snappoint_request.argtypes = [ctypes.c_void_p, ctypes.c_longlong, ctypes.c_char_p]

        self._osl_save_snappoint_request.restype = ctypes.c_bool

 

        self._osl_load_snappoint_request = ctypes.cdll.OneSimLink.LoadSnapPointRequest

        self._osl_load_snappoint_request.argtypes = [ctypes.c_void_p, ctypes.c_longlong]

        self._osl_load_snappoint_request.restype = ctypes.c_bool

 

        self._osl_get_session_mode = ctypes.cdll.OneSimLink.GetRecorderMode

        self._osl_get_session_mode.restype = ctypes.c_int

 

        self._osl_get_recording_time_ms = ctypes.cdll.OneSimLink.GetRecordingTimeMsec

        self._osl_get_recording_time_ms.restype = ctypes.c_longlong

 

        self._osl_get_last_recorder_command_message = ctypes.cdll.OneSimLink.GetLastSessionCommandMessage

        self._osl_get_last_recorder_command_message.restype = ctypes.c_char_p

 

        ###################################

        # Session Store / Load

        ###################################

 

        self._osl_store_current_session_configuration = ctypes.cdll.OneSimLink.StoreCurrentSessionConfiguration

        self._osl_store_current_session_configuration.argtypes = [ctypes.c_char_p]

        self._osl_store_current_session_configuration.restype = ctypes.c_bool

 

        self._osl_load_session_configuration = ctypes.cdll.OneSimLink.LoadSessionConfiguration

        self._osl_load_session_configuration.argtypes = [ctypes.c_char_p]

        self._osl_load_session_configuration.restype = ctypes.c_bool

 

        ###################################

        # Models

        ###################################

 

        self._osl_send_station_model_message = ctypes.cdll.OneSimLink.SendStationModelMessage

        self._osl_send_station_model_message.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]

        self._osl_send_station_model_message.restype = ctypes.c_bool

 

        self.StationMessageRespondFuncType = ctypes.CFUNCTYPE(None, ctypes.c_char_p)

        self._osl_send_station_model_message_and_wait_for_response = ctypes.cdll.OneSimLink.SendStationModelMessageAndWaitForResponse

        self._osl_send_station_model_message_and_wait_for_response.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, self.StationMessageRespondFuncType, ctypes.c_uint]

        self._osl_send_station_model_message_and_wait_for_response.restype = ctypes.c_bool

 

        self._osl_set_mmi_socket_sync_mode = ctypes.cdll.OneSimLink.SetMmiSocketSyncMode

        self._osl_set_mmi_socket_sync_mode.argtypes = [ctypes.c_bool, ctypes.c_uint]

 

        ###################################

        # Other

        ###################################

 

        self._osl_is_connected_to_sns = ctypes.cdll.OneSimLink.IsConnectedToSns

        self._osl_is_connected_to_sns.restype = ctypes.c_bool

 

        # Initialize connection

        self._init_ok = self._osl_onesim_link_startup()

        if self._init_ok == False:

            self._initerror = self._osl_get_error().decode('utf-8')

            raise Exception("Failed to initialize one-sim-link.", self._initerror)

        else:

            self._initerror = ''

 

    def server_update(self):

        self._osl_server_update()

 

#=============================================================================

# Elements

#=============================================================================

 

#########################################################################

    def get_lru_def_names(self):

        ''' Return a list of available LRU-definitions'''

        _num_of_lrus = self._osl_get_amount_of_defined_lrus()

        return [self._osl_get_lru_def_name(i).decode('utf-8') for i in range(_num_of_lrus)]

#########################################################################

    def get_lrus_names(self):

        ''' Deprecated (use get_lru_def_names)'''

        return self.get_lru_def_names()

#########################################################################

    def get_blocks_names(self, lru_def_name):

        ''' Return a list of block-definitions names in the required LRU-definitions.

        'lru_def_name' should be a string of an existing LRU-definitions

        '''

        _lru_def_id = list(self.get_lru_def_names()).index(lru_def_name)

        _num_of_block_defs = self._osl_get_amount_of_block_defs(_lru_def_id)

        return [self._osl_get_block_name(self._osl_get_block_def_id(_lru_def_id, i)).decode('utf-8') for i in range(_num_of_block_defs)]

 

#########################################################################

    def get_elements_names(self, full_block_name):

        ''' Return a list of elements in the required block

        full_block_name should be a string in the format of 'entity.lru.block' of an existing block and lru

        '''

        _elements = list()

        _current_block_id = self._osl_get_block_id_by_name(full_block_name.encode('utf-8'))

        _current_block_def_id = _osl_get_block_def_id_from_block(_current_block_id)

        if _current_block_id > -1:

            _num_of_elements = self._osl_get_block_def_amount_of_elements(_current_block_def_id)

            _elements = [self._osl_get_def_element_name(_current_block_def_id, i).decode('utf-8') for i in range(_num_of_elements)]

        return _elements

 

#########################################################################

    def publish_elements(self, elements):

        elements_status = list() # Tuples of (element, valid)

        for element in elements:

            element_valid = False

            with self._registered_elements_lock:

                element_reg_id = self._registered_elements.get(element)

                if element_reg_id is None:

                    is_valid, element_block, element_name = self.__parse_element(element)

                    if is_valid:

                        element_reg_id = self._osl_register_element(element_block.encode(), element_name.encode(), True, True)

                        if element_reg_id > -1:

                            self._registered_elements[element] = element_reg_id

                            self._reveresed_registered_elements[element_reg_id] = element

                            element_valid = True

                else:

                    element_valid = True

            elements_status.append((element, element_valid))

        # Wait for SHMEM to update

        time.sleep(0.1)

        return elements_status

 

#########################################################################

    #Errors/Exceptions: ElementNotDefinedException, ERROR_NOT_SAMPLED, ERROR_SAMPLE_TIMEOUT

    def get_element_value(self, element, unit = '', sample_timeout_ms = sys.maxsize):

        self.__clear_error()

        retval = None

        element_valid, element_reg_id = self.__register_element(element)

        if element_valid:

            is_sampled = self.is_element_sampled(element)

            if not is_sampled:

                # Wait for SHMEM to update

                time.sleep(0.1)

            eng_format = 0

            if self._osl_get_element_value_for_scripts(ctypes.byref(self._err), element_reg_id, self._val, self._ELEMENT_BUFFER_SIZE, unit.encode(), eng_format, sample_timeout_ms):

                retval = self._val.value.decode()

        else:

            self._err.value = _ErrorType.ERROR_INVALID_ELEMENT.value

 

        if self._err.value == _ErrorType.ERROR_INVALID_ELEMENT.value:

            raise ElementNotDefinedException("element doesn't exist in simulation, element = " + element)

        return retval

 

#########################################################################

    #Errors/Exceptions: ElementNotDefinedException

    def wait_for_element_value(self, element, expected_value, timeout_sec = sys.maxsize, unit = ''):

        if type(expected_value) == int or type(expected_value) == float:

            element_equals = lambda value: float(value) == expected_value

        else:

            element_equals = lambda value: value == expected_value

        return self.__timeout_element_condition(element, unit, element_equals, timeout_sec)

 

#########################################################################

    #Errors/Exceptions: ElementNotDefinedException

    def wait_for_element_value_within_range(self, element, expected_min_value, expected_max_value, timeout_sec = sys.maxsize, unit = ''):

        element_in_range = lambda value: expected_min_value <= float(value) <= expected_max_value

        return self.__timeout_element_condition(element, unit, element_in_range, timeout_sec)

 

#########################################################################

    #Errors/Exceptions: ElementNotDefinedException

    def wait_for_element_value_condition(self, element, condition, timeout_sec = sys.maxsize, unit = ''):

        return self.__timeout_element_condition(element, unit, condition, timeout_sec)

 

#########################################################################

    #Errors/Exceptions: ElementNotDefinedException, ERROR_NOT_SAMPLED, ERROR_SAMPLE_TIMEOUT

    def get_element_raw_value(self, element, format, sample_timeout_ms = sys.maxsize):

        self.__clear_error()

        retval = None

        element_valid, element_reg_id = self.__register_element(element)

        if element_valid:

            is_sampled = self.is_element_sampled(element)

            if not is_sampled:

                # Wait for SHMEM to update

                time.sleep(0.1)

            unit = ''

            if self._osl_get_element_value_for_scripts(ctypes.byref(self._err), element_reg_id, self._val, self._ELEMENT_BUFFER_SIZE, unit.encode(), format, sample_timeout_ms):

                retval = self._val.value.decode()

        else:

            self._err.value = _ErrorType.ERROR_INVALID_ELEMENT.value

 

        if self._err.value == _ErrorType.ERROR_INVALID_ELEMENT.value:

            raise ElementNotDefinedException("element doesn't exist in simulation, element = " + element)

        return retval

#########################################################################

    #Errors/Exceptions: ElementNotDefinedException

    def set_element_value_request(self, element, value, unit = ''):

        self.__clear_error()

        element_valid, element_reg_id = self.__register_element(element)

        inject_ok = False

        if element_valid:

            eng_format = 0

            if self._osl_set_element_value_request_for_scripts(ctypes.byref(self._err), element_reg_id, value.encode(), unit.encode(), eng_format, False, True):

                inject_ok = True

                self._osl_send_pending_requests()

        else:

            self._err.value = _ErrorType.ERROR_INVALID_ELEMENT.value

 

        if self._err.value == _ErrorType.ERROR_INVALID_ELEMENT.value:

            raise ElementNotDefinedException("Element '" + element + "' doesn't exist")

        if self._err.value == _ErrorType.ERROR_INVALID_ARGUMENTS.value:

            raise InvalidArgumentException("Invalid arguments (value '" + value + "' might be invalid for element '" + element + "')")

        assert inject_ok == True, "Unknown error - " + str(self._err.value)

#########################################################################

    #Errors/Exceptions: ElementNotDefinedException, InvalidArgumentException

    def set_element_raw_value_request(self, element, value, format):

        self.__clear_error()

        element_valid, element_reg_id = self.__register_element(element)

        inject_ok = False

        if element_valid:

            unit = ''

            if self._osl_set_element_value_request_for_scripts(ctypes.byref(self._err), element_reg_id, value.encode(), unit.encode(), format, False, True):

                inject_ok = True

                self._osl_send_pending_requests()

        else:

            self._err.value = _ErrorType.ERROR_INVALID_ELEMENT.value

 

        if self._err.value == _ErrorType.ERROR_INVALID_ELEMENT.value:

            raise ElementNotDefinedException("element doesn't exist in simulation, element = " + element)

        elif self._err.value == _ErrorType.ERROR_INVALID_ARGUMENTS.value:

            raise InvalidArgumentException("value size is wrong")

        assert inject_ok == True, "Unknown error - " + self._err.value

#########################################################################

    #Errors/Exceptions: ElementNotDefinedException

    def inject_element_value_request(self, element, value, unit = ''):

        self.__clear_error()

        element_valid, element_reg_id = self.__register_element(element)

        inject_ok = False

        if element_valid:

            eng_format = 0

            if self._osl_set_element_value_request_for_scripts(ctypes.byref(self._err), element_reg_id, value.encode(), unit.encode(), eng_format, False, False):

                inject_ok = True

                self._osl_send_pending_requests()

        else:

            self._err.value = _ErrorType.ERROR_INVALID_ELEMENT.value

 

        if self._err.value == _ErrorType.ERROR_INVALID_ELEMENT.value:

            raise ElementNotDefinedException("element doesn't exist in simulation, element = " + element)

        assert inject_ok == True, "Unknown error - " + self._err.value

#########################################################################

    #Errors/Exceptions: ElementNotDefinedException, InvalidArgumentException

    def inject_element_raw_value_request(self, element, value, format):

        self.__clear_error()

        element_valid, element_reg_id = self.__register_element(element)

        inject_ok = False

        if element_valid:

            unit = ''

            if self._osl_set_element_value_request_for_scripts(ctypes.byref(self._err), element_reg_id, value.encode(), unit.encode(), format, False, False):

                inject_ok = True

                self._osl_send_pending_requests()

        else:

            self._err.value = _ErrorType.ERROR_INVALID_ELEMENT.value

 

        if self._err.value == _ErrorType.ERROR_INVALID_ELEMENT.value:

            raise ElementNotDefinedException("element doesn't exist in simulation, element = " + element)

        elif self._err.value == _ErrorType.ERROR_INVALID_ARGUMENTS.value:

            raise InvalidArgumentException("value size is wrong")

        assert inject_ok == True, "Unknown error - " + self._err.value

#########################################################################

    def element_exists(self, element):

        self.__clear_error()

        exist = self._osl_element_exists_for_script(element.encode())

        return exist

#########################################################################

    #Errors/Exceptions: ElementNotDefinedException

    def is_element_sampled(self, element):

        self.__clear_error()

        element_valid, element_reg_id = self.__register_element(element)

        sampled = False

        if element_valid:

            if self._osl_is_element_sampled(element_reg_id):

                sampled = True

        else:

            self._err.value = _ErrorType.ERROR_INVALID_ELEMENT.value

 

        if self._err.value == _ErrorType.ERROR_INVALID_ELEMENT.value:

            raise ElementNotDefinedException("element doesn't exist in simulation, element = " + element)

        return sampled

#########################################################################

    #Errors/Exceptions: ElementNotDefinedException

    def is_element_applied(self, element):

        self.__clear_error()

        element_valid, element_reg_id = self.__register_element(element)

        applied = False

        if element_valid:

            if self._osl_is_element_applied(element_reg_id):

                applied = True

        else:

            self._err.value = _ErrorType.ERROR_INVALID_ELEMENT.value

 

        if self._err.value == _ErrorType.ERROR_INVALID_ELEMENT.value:

            raise ElementNotDefinedException("element doesn't exist in simulation, element = " + element)

        return applied

#########################################################################

    #Errors/Exceptions: ElementNotDefinedException

    def unapply_element_request(self, element):

        self.__clear_error()

        element_valid, element_reg_id = self.__register_element(element)

        wasSent = False

        if element_valid:

            self._osl_element_unapply_request(element_reg_id)

            wasSent = True

            self._osl_send_pending_requests()

        else:

            self._err.value = _ErrorType.ERROR_INVALID_ELEMENT.value

 

        if self._err.value == _ErrorType.ERROR_INVALID_ELEMENT.value:

            raise ElementNotDefinedException("element doesn't exist in simulation, element = " + element)

        assert wasSent == True, "Unknown error - " + self._err.value

#########################################################################

    def unapply_all_elements_request(self):

        self.__clear_error()

        with self._registered_elements_lock:

            for element, element_reg_id in self._registered_elements.items():

                if element_reg_id is not None and element_reg_id >= 0:

                    self._osl_element_unapply_request(element_reg_id)

        self._osl_send_pending_requests()

#########################################################################

    def unapply_all_elements(self):

        self.unapply_all_elements_request()

        time.sleep(0.01)

        self.__clear_error()

        with self._registered_elements_lock:

            _temp_elements = self._registered_elements.items()

        for element, element_reg_id in _temp_elements:

            if element_reg_id is not None and element_reg_id >= 0:

                if self.is_element_applied(element):

                    self._osl_element_unapply_request(element_reg_id)

                    self._osl_send_pending_requests()

                    for i in range(100):

                        if self.is_element_applied(element):

                            time.sleep(0.01)

                        else:

                            break

        self._osl_send_pending_requests()

#########################################################################

    #Errors/Exceptions: ElementNotDefinedException

    def get_element_properties(self, element):

        self.__clear_error()

        element_valid, element_reg_id = self.__register_element(element)

        if element_valid:

            block_def_id = self._osl_get_element_block_def_id(element_reg_id)

            element_index = self._osl_get_element_index_in_block(element_reg_id)

            if block_def_id >= 0 and element_index >= 0:

                element = Element()

                element.name = self._osl_get_def_element_name(block_def_id, element_index).decode('utf-8')

                element.block_name = self._osl_get_block_name(block_def_id, element_index).decode('utf-8')

                element.description = self._osl_get_def_element_description(block_def_id, element_index).decode('utf-8')

                element.type = self._osl_get_def_element_type(block_def_id, element_index).decode('utf-8')

                element.raw_data_type = EngType(self._osl_get_def_element_eng_type(block_def_id, element_index))

                element.eng_data_type = RawType(self._osl_get_def_element_raw_type(block_def_id, element_index))

                element.base_unit = self._osl_get_def_element_default_unit(block_def_id, element_index)

                element.base_unit = element.base_unit.decode('utf-8') if element.base_unit is not None else None

                element.byte_offset = self._osl_get_def_element_byte_offset(block_def_id, element_index)

                element.bit_offset = self._osl_get_def_element_bit_offset(block_def_id, element_index)

                element.raw_size_in_bits = self._osl_get_def_element_raw_size_in_bits(block_def_id, element_index)

                element.raw_size_in_bytes = self._osl_get_def_element_raw_size_in_bytes(block_def_id, element_index)

                element.eng_size_in_bytes = self._osl_get_def_element_eng_size_in_bytes(block_def_id, element_index)

                element.scale = self._osl_get_def_element_scale(block_def_id, element_index)

                element.scale_offset = self._osl_get_def_element_scale_offset(block_def_id, element_index)

                element.low_value = self._osl_get_def_element_range_low_value(block_def_id, element_index)

                element.high_value = self._osl_get_def_element_range_high_value(block_def_id, element_index)

                for i in range(self._osl_get_def_element_amount_of_discretes(block_def_id, element_index)):

                    k = self._osl_get_def_element_discrete_key(block_def_id, element_index, i).decode('utf-8')

                    v = self._osl_get_def_element_discrete_value(block_def_id, element_index, i)

                    element.discretes[k] = v

                return element

        else:

            self._err.value = _ErrorType.ERROR_INVALID_ELEMENT.value

 

        if self._err.value == _ErrorType.ERROR_INVALID_ELEMENT.value:

            raise ElementNotDefinedException("element doesn't exist in simulation, element = " + element)

        return None

#########################################################################

    def unapply_on_exit(self, unapply_on_exit):

        self.__clear_error()

        self._osl_unapply_on_exit(unapply_on_exit)

 

#=============================================================================

# Entities

#=============================================================================

 

#########################################################################

    def get_num_of_entities(self):

        self.__clear_error()

        retval = self._osl_get_num_of_entities()

        return retval

#########################################################################

    def entity_exists(self, entity_name, check_model_init_done = True):

        self.__clear_error()

        entity_id = self._osl_get_entity_id(entity_name.encode())

        if entity_id >= 0: # Entity Exists

            if check_model_init_done:

                model_init_done = self.get_entity_model_init_done(entity_id)

                return model_init_done

            else:

                return True

        return False

#########################################################################

    #Errors/Exceptions: EntityNotDefinedException

    def get_entity_id(self, entity_name):

        self.__clear_error()

        entity_id = self._osl_get_entity_id(entity_name.encode())

        if entity_id < 0:

            raise EntityNotDefinedException("entity doesn't exist in simulation, entity = " + entity_name)

        return entity_id

#########################################################################

    #Errors/Exceptions: EntityNotDefinedException

    def get_entity_attributes(self, entity_id_or_name):

        self.__clear_error()

        entity_id = self.__get_entity_id(entity_id_or_name) # Throws EntityNotDefinedException

        ent = Entity()

        ent.entity_id = entity_id

        bDis = self._osl_get_entity_dis_as_string(ctypes.byref(self._err), entity_id)

        if (self._err.value == _ErrorType.ERROR_UNDEFINED_ENTITY.value or

                self._err.value == _ErrorType.ERROR_DISABLED_WHILE_INITS.value):

            raise EntityNotDefinedException("entity doesn't exist in simulation")

        if (self._err.value == _ErrorType.ERROR_NONE.value):

            ent.dis = bDis.decode("utf-8")

        elif (self._err.value == _ErrorType.ERROR_DIS_TYPE_NOT_DEFINED.value):

            ent.dis = ''

        self.__clear_error()

        ent.full_name = self._osl_get_entity_name(entity_id).decode("utf-8")

        ent.type = self._osl_get_entity_type_name(entity_id).decode("utf-8")

        uniqueId = ctypes.c_uint()

        parentId = ctypes.c_int()

        aggregatorId = ctypes.c_int()

        stationId = ctypes.c_uint()

        typeId = ctypes.c_uint()

        active = ctypes.c_bool()

        publish = ctypes.c_bool()

        is_reflected = ctypes.c_bool()

        retval = self._osl_get_entity_attributes(ctypes.byref(self._err),

                                                    entity_id,

                                                    ctypes.byref(uniqueId),

                                                    ctypes.byref(parentId),

                                                    ctypes.byref(aggregatorId),

                                                    ctypes.byref(active),

                                                    ctypes.byref(publish),

                                                    ctypes.byref(is_reflected),

                                                    ctypes.byref(stationId),

                                                    ctypes.byref(typeId))

        if retval == True:

            station_name = self._osl_get_station_name_by_id(stationId)

            ent.station = station_name.decode("utf-8")

            ent.uniqueId = uniqueId.value

            ent.parent = ''

            ent.aggregator = ''

            ent.active = active.value

            ent.publish = publish.value

            ent.is_reflected = is_reflected.value

            ent.entityTypeId = typeId.value

            if parentId.value >= 0:

                ent.parent = self._osl_get_entity_name(parentId.value).decode("utf-8")

            if aggregatorId.value >= 0:

                ent.aggregator = self._osl_get_entity_name(aggregatorId.value).decode("utf-8")

 

        if (self._err.value == _ErrorType.ERROR_UNDEFINED_ENTITY.value or

                self._err.value == _ErrorType.ERROR_DISABLED_WHILE_INITS.value):

            raise EntityNotDefinedException("entity doesn't exist in simulation")

        assert retval == True, "Unknown error - " + self._err.value

        return ent

#########################################################################

    #Errors/Exceptions: EntityNotDefinedException, OneSimLinkConfigurationException, TimeOutException, ERROR_NOT_SAMPLED

    def get_entity_position(self, entity_id_or_name):

        position = None

        timeout_in_seconds = 10

        sleep_interval = 0.1

        while position is None:

            position = self.internal_get_entity_position(entity_id_or_name)

            time.sleep(sleep_interval)

            timeout_in_seconds -= sleep_interval

            if timeout_in_seconds <= 0:

                raise TimeOutException("failed to get entity position (time-out), entity = " + entity_id_or_name)

        return position

#########################################################################

    #Errors/Exceptions: EntityNotDefinedException, OneSimLinkConfigurationException, ERROR_NOT_SAMPLED

    def internal_get_entity_position(self, entity_id_or_name):

        self.__clear_error()

        entity_id = self.__get_entity_id(entity_id_or_name) # Throws EntityNotDefinedException

        pos = Position()

        latitude = ctypes.c_double()

        longitude = ctypes.c_double()

        heading = ctypes.c_double()

        altitude_sea = ctypes.c_double()

        altitude_ground = ctypes.c_double()

        pitch = ctypes.c_double()

        roll = ctypes.c_double()

        x = ctypes.c_double()

        y = ctypes.c_double()

        z = ctypes.c_double()

        retval = self._osl_get_entity_position(ctypes.byref(self._err),

                                            entity_id,

                                            ctypes.byref(latitude),

                                            ctypes.byref(longitude),

                                            ctypes.byref(heading),

                                            ctypes.byref(altitude_sea),

                                            ctypes.byref(altitude_ground),

                                            ctypes.byref(pitch),

                                            ctypes.byref(roll),

                                            ctypes.byref(x),

                                            ctypes.byref(y),

                                            ctypes.byref(z))

        if (self._err.value == _ErrorType.ERROR_UNDEFINED_ENTITY.value or

                self._err.value == _ErrorType.ERROR_INACTIVE_ENTITY.value or

                self._err.value == _ErrorType.ERROR_DISABLED_WHILE_INITS.value):

            raise EntityNotDefinedException("entity doesn't exist in simulation")

        if (self._err.value == _ErrorType.ERROR_CONFIGURATION.value):

            raise OneSimLinkConfigurationException("check configuration in %SIMPATH_COMMON%Setups/OneSimLinkConfiguration.ini")

        if (self._err.value == _ErrorType.ERROR_INVALID_OP.value):

            raise InvalidOperationException("entity doesn't contain device for position")

        if retval == False:

            assert self._err.value == _ErrorType.ERROR_NOT_SAMPLED.value, "Unknown error - " + self._err.value

            return None

        else:

            pos.latitude = latitude.value

            pos.longitude = longitude.value

            pos.heading = heading.value

            pos.altitude_sea = altitude_sea.value

            pos.altitude_ground = altitude_ground.value

            pos.pitch = pitch.value

            pos.roll = roll.value

            pos.x = x.value

            pos.y = y.value

            pos.z = z.value

        return pos

#########################################################################

    #Errors/Exceptions: EntityNotDefinedException, OneSimLinkConfigurationException

    def set_entity_position_request(self,

                                    entity_id_or_name,

                                    latitude,

                                    longitude,

                                    heading = sys.float_info.max,

                                    altitude_sea = sys.float_info.max,

                                    pitch = sys.float_info.max,

                                    roll = sys.float_info.max,

                                    tas = sys.float_info.max):

        self.__clear_error()

        entity_id = self.__get_entity_id(entity_id_or_name) # Throws EntityNotDefinedException

        retval = self._osl_set_entity_position_request(ctypes.byref(self._err),

                                                        entity_id,

                                                        latitude,

                                                        longitude,

                                                        heading,

                                                        altitude_sea,

                                                        pitch,

                                                        roll,

                                                        tas)

        if (self._err.value == _ErrorType.ERROR_UNDEFINED_ENTITY.value or

                self._err.value == _ErrorType.ERROR_INACTIVE_ENTITY.value or

                self._err.value == _ErrorType.ERROR_DISABLED_WHILE_INITS.value):

            raise EntityNotDefinedException("entity doesn't exist in simulation")

        if (self._err.value == _ErrorType.ERROR_CONFIGURATION.value):

            raise OneSimLinkConfigurationException("check configuration in %SIMPATH_COMMON%Setups/OneSimLinkConfiguration.ini")

        if (self._err.value == _ErrorType.ERROR_INVALID_OP.value):

            raise InvalidOperationException("entity doesn't contain device for position")

        self._osl_send_pending_requests()

        assert retval == True, "Unknown error - " + self._err.value

#########################################################################

    #Errors/Exceptions: EntityNotDefinedException, OneSimLinkConfigurationException, InvalidOperationException, ERROR_NOT_SAMPLED

    def get_entity_kind(self, entity_id_or_name):

        self.__clear_error()

        entity_id = self.__get_entity_id(entity_id_or_name) # Throws EntityNotDefinedException

        kind = ctypes.c_int()

        retval = self._osl_get_entity_kind(ctypes.byref(self._err),

                                            entity_id,

                                            ctypes.byref(kind))

        if (self._err.value == _ErrorType.ERROR_UNDEFINED_ENTITY.value or

                self._err.value == _ErrorType.ERROR_INACTIVE_ENTITY.value or

                self._err.value == _ErrorType.ERROR_DISABLED_WHILE_INITS.value):

            raise EntityNotDefinedException("entity doesn't exist in simulation")

        if (self._err.value == _ErrorType.ERROR_CONFIGURATION.value):

            raise OneSimLinkConfigurationException("check configuration in %SIMPATH_COMMON%Setups/OneSimLinkConfiguration.ini")

        if (self._err.value == _ErrorType.ERROR_INVALID_OP.value):

            raise InvalidOperationException("entity doesn't contain device for kind")

        if retval == False:

            assert self._err.value == _ErrorType.ERROR_NOT_SAMPLED.value, "Unknown error - " + self._err.value

            return None

        return KindType(kind.value)

#########################################################################

    #Errors/Exceptions: EntityNotDefinedException, OneSimLinkConfigurationException, InvalidOperationException

    def set_entity_kind(self, entity_id_or_name, kind):

        self.__clear_error()

        entity_id = self.__get_entity_id(entity_id_or_name) # Throws EntityNotDefinedException

        retval = self._osl_set_entity_kind(ctypes.byref(self._err), entity_id, kind)

        if (self._err.value == _ErrorType.ERROR_UNDEFINED_ENTITY.value or

                self._err.value == _ErrorType.ERROR_INACTIVE_ENTITY.value or

                self._err.value == _ErrorType.ERROR_DISABLED_WHILE_INITS.value):

            raise EntityNotDefinedException("entity doesn't exist in simulation")

        if (self._err.value == _ErrorType.ERROR_CONFIGURATION.value):

            raise OneSimLinkConfigurationException("check configuration in %SIMPATH_COMMON%Setups/OneSimLinkConfiguration.ini")

        if (self._err.value == _ErrorType.ERROR_INVALID_OP.value):

            raise InvalidOperationException("entity doesn't contain device for kind")

        assert retval == True, "Unknown error - " + self._err.value

#########################################################################

    #Errors/Exceptions: EntityNotDefinedException, OneSimLinkConfigurationException, InvalidOperationException, ERROR_NOT_SAMPLED

    def get_entity_model_init_done(self, entity_id_or_name):

        self.__clear_error()

        entity_id = self.__get_entity_id(entity_id_or_name) # Throws EntityNotDefinedException

        model_init_done = ctypes.c_bool()

        retval = self._osl_get_entity_model_init_done(ctypes.byref(self._err),

                                            entity_id,

                                            ctypes.byref(model_init_done))

        if (self._err.value == _ErrorType.ERROR_UNDEFINED_ENTITY.value or

                self._err.value == _ErrorType.ERROR_INACTIVE_ENTITY.value or

                self._err.value == _ErrorType.ERROR_DISABLED_WHILE_INITS.value):

            raise EntityNotDefinedException("entity doesn't exist in simulation")

        if retval == False:

            assert self._err.value == _ErrorType.ERROR_NOT_SAMPLED.value, "Unknown error - " + self._err.value

            return None

        return bool(model_init_done.value)

#########################################################################

    def add_entity_request(self, entity_name,

                            type_name_or_dis,

                            load_balance_in_stations = True,

                            station_name = '',

                            published = True,

                            kind = KindType.KIND_OTHER,

                            latitude = sys.float_info.max,

                            longitude = sys.float_info.max,

                            heading = sys.float_info.max,

                            altitude_sea = sys.float_info.max,

                            pitch = sys.float_info.max,

                            roll = sys.float_info.max,

                            tas = sys.float_info.max,

                            elementNames = None,

                            elementValues = None):

        self.__clear_error()

        # Creating string array for elementNames, elementValues

        amountOfNames = 0

        amountOfValues = 0

        arrValues = None

        arrName = None

        if elementNames is not None:

            amountOfNames = len(elementNames)

        if elementValues is not None:

            amountOfValues = len(elementValues)

        assert amountOfNames == amountOfValues, "Invalid argument - elementNames.size != elementValues.size"

        if amountOfNames > 0:

            arrName = (ctypes.c_char_p * amountOfNames)()

            for idx in range(amountOfNames):

                arrName[idx] = elementNames[idx].encode()

        if amountOfValues > 0:

            arrValues = (ctypes.c_char_p * amountOfValues)()

            for idx in range(amountOfValues):

                arrValues[idx] = elementValues[idx].encode()

        retval = self._osl_add_entity_request(ctypes.byref(self._err),

                                            entity_name.encode(),

                                            type_name_or_dis.encode(),

                                            load_balance_in_stations,

                                            station_name.encode(),

                                            published,

                                            kind,

                                            latitude,

                                            longitude,

                                            heading,

                                            altitude_sea,

                                            pitch,

                                            roll,

                                            tas,

                                            arrName,

                                            arrValues,

                                            amountOfNames)

        if (self._err.value == _ErrorType.ERROR_CONFIGURATION.value):

            raise OneSimLinkConfigurationException("check configuration in %SIMPATH_COMMON%Setups/OneSimLinkConfiguration.ini")

        if (self._err.value == _ErrorType.ERROR_INVALID_ARGUMENTS.value):

            raise InvalidArgumentException("")

        if (self._err.value == _ErrorType.ERROR_DISABLED_WHILE_INITS.value):

            raise InvalidOperationException("cannot add entity during sim-engine initialization")

        self._osl_send_pending_requests()

        assert retval == True, "Unknown error - " + self._err.value

#########################################################################

    def add_entity(self, entity_name,

                    type_name_or_dis,

                    load_balance_in_stations = True,

                    station_name = '',

                    published = True,

                    kind = KindType.KIND_OTHER,

                    latitude = sys.float_info.max,

                    longitude = sys.float_info.max,

                    heading = sys.float_info.max,

                    altitude_sea = sys.float_info.max,

                    pitch = sys.float_info.max,

                    roll = sys.float_info.max,

                    tas = sys.float_info.max,

                    elementNames = None,

                    elementValues = None,

                    timeout_ms = sys.maxsize):

        self.add_entity_request(entity_name,

                            type_name_or_dis,

                            load_balance_in_stations,

                            station_name,

                            published,

                            kind,

                            latitude,

                            longitude,

                            heading,

                            altitude_sea,

                            pitch,

                            roll,

                            tas,

                            elementNames,

                            elementValues)

        _timeout_s = timeout_ms / 1000.0

        _check_interval = 0.01

        _ended_ok = False

        while _timeout_s > 0:

            if self.entity_exists(entity_name):

                _ended_ok = True

                break

            else:

                _timeout_s -= _check_interval

                time.sleep(_check_interval)

        return _ended_ok

#########################################################################

    def add_entity_with_params_request(self, entity_name,

                                        type_name_or_dis,

                                        load_balance_in_stations = True,

                                        station_name = '',

                                        published = True,

                                        elementNames = None,

                                        elementValues = None):

        self.__clear_error()

        # Creating string array for elementNames, elementValues

        amountOfNames = 0

        amountOfValues = 0

        arrValues = None

        arrName = None

        if elementNames is not None:

            amountOfNames = len(elementNames)

        if elementValues is not None:

            amountOfValues = len(elementValues)

        assert amountOfNames == amountOfValues, "Invalid argument - elementNames.size != elementValues.size"

        if amountOfNames > 0:

            arrName = (ctypes.c_char_p * amountOfNames)()

            for idx in range(amountOfNames):

                arrName[idx] = elementNames[idx].encode()

        if amountOfValues > 0:

            arrValues = (ctypes.c_char_p * amountOfValues)()

            for idx in range(amountOfValues):

                arrValues[idx] = elementValues[idx].encode()

        retval = self._osl_add_entity_with_params_request(ctypes.byref(self._err),

                                                            entity_name.encode(),

                                                            type_name_or_dis.encode(),

                                                            load_balance_in_stations,

                                                            station_name.encode(),

                                                            published,

                                                            arrName,

                                                            arrValues,

                                                            amountOfNames)

        if (self._err.value == _ErrorType.ERROR_CONFIGURATION.value):

            raise OneSimLinkConfigurationException("check configuration in %SIMPATH_COMMON%Setups/OneSimLinkConfiguration.ini")

        if (self._err.value == _ErrorType.ERROR_INVALID_ARGUMENTS.value):

            raise InvalidArgumentException("failed to create entity due to invalid parameter values (e.g. entity name might be illegal or already in used; invalid type name; etc.)") #TODO need to provide proper diagnostics

        if (self._err.value == _ErrorType.ERROR_DISABLED_WHILE_INITS.value):

            raise InvalidOperationException("cannot add entity during sim-engine initialization")

        self._osl_send_pending_requests()

        assert retval == True, "Unknown error - " + self._err.value

#########################################################################

    def add_entity_with_params(self, entity_name,

                                type_name_or_dis,

                                load_balance_in_stations = True,

                                station_name = '',

                                published = True,

                                elementNames = None,

                                elementValues = None,

                                timeout_ms = sys.maxsize):

        self.add_entity_with_params_request(entity_name,

                                            type_name_or_dis,

                                            load_balance_in_stations,

                                            station_name,

                                            published,

                                            elementNames,

                                            elementValues)

        _timeout_s = timeout_ms / 1000.0

        _check_interval = 0.01

        _ended_ok = False

        while _timeout_s > 0:

            if self.entity_exists(entity_name):

                _ended_ok = True

                break

            else:

                _timeout_s -= _check_interval

                time.sleep(_check_interval)

        return _ended_ok

#########################################################################

    def duplicate_entity_request(self, source_entity_id_or_name,

                                        entity_name,

                                        latitude = sys.float_info.max,

                                        longitude = sys.float_info.max,

                                        altitude_sea = sys.float_info.max,

                                        duplicate_aggregation = True,

                                        elementNames = None,

                                        elementValues = None,

                                        propagate_elements_to_aggregation = False):

        self.__clear_error()

        # Creating string array for elementNames, elementValues

        amountOfNames = 0

        amountOfValues = 0

        arrValues = None

        arrName = None

        if elementNames is not None:

            amountOfNames = len(elementNames)

        if elementValues is not None:

            amountOfValues = len(elementValues)

        assert amountOfNames == amountOfValues, "Invalid argument - elementNames.size != elementValues.size"

        if amountOfNames > 0:

            arrName = (ctypes.c_char_p * amountOfNames)()

            for idx in range(amountOfNames):

                arrName[idx] = elementNames[idx].encode()

        if amountOfValues > 0:

            arrValues = (ctypes.c_char_p * amountOfValues)()

            for idx in range(amountOfValues):

                arrValues[idx] = elementValues[idx].encode()

        sourceEntityId = self.__get_entity_id(source_entity_id_or_name) # Throws EntityNotDefinedException

        retval = self._osl_duplicate_entity_request(ctypes.byref(self._err),

                                                    sourceEntityId,

                                                    entity_name.encode(),

                                                    latitude,

                                                    longitude,

                                                    altitude_sea,

                                                    duplicate_aggregation,

                                                    arrName,

                                                    arrValues,

                                                    amountOfNames,

                                                    propagate_elements_to_aggregation)

        if (self._err.value == _ErrorType.ERROR_UNDEFINED_ENTITY.value or

                self._err.value == _ErrorType.ERROR_INACTIVE_ENTITY.value or

                self._err.value == _ErrorType.ERROR_DISABLED_WHILE_INITS.value):

            raise EntityNotDefinedException("entity doesn't exist in simulation")

        if (self._err.value == _ErrorType.ERROR_CONFIGURATION.value):

            raise OneSimLinkConfigurationException("check configuration in %SIMPATH_COMMON%Setups/OneSimLinkConfiguration.ini")

        if (self._err.value == _ErrorType.ERROR_INVALID_ARGUMENTS.value):

            raise InvalidArgumentException("")

        if (self._err.value == _ErrorType.ERROR_DISABLED_WHILE_INITS.value):

            raise InvalidOperationException("cannot add entity during sim-engine initialization")

        if (self._err.value == _ErrorType.ERROR_INVALID_OP.value):

            raise InvalidOperationException("entity doesn't contain device for position")

        self._osl_send_pending_requests()

        assert retval == True, "Unknown error - " + self._err.value

#########################################################################

    #Errors/Exceptions: EntityNotDefinedException

    def remove_entity_request(self, entity_id_or_name, remove_aggregation = False):

        self.__clear_error()

        entity_id = self.__get_entity_id(entity_id_or_name) # Throws EntityNotDefinedException

        retval = self._osl_remove_entity_request(ctypes.byref(self._err), entity_id, remove_aggregation)

        if (self._err.value == _ErrorType.ERROR_UNDEFINED_ENTITY.value or

                self._err.value == _ErrorType.ERROR_INACTIVE_ENTITY.value or

                self._err.value == _ErrorType.ERROR_DISABLED_WHILE_INITS.value):

            raise EntityNotDefinedException("entity doesn't exist in simulation")

        self._osl_send_pending_requests()

        assert retval == True, "Unknown error - " + self._err.value

#########################################################################

    #Errors/Exceptions: EntityNotDefinedException

    def remove_entity(self, entity_id_or_name, remove_aggregation = False, timeout_ms = sys.maxsize):

        self.removed_entity_id_or_name = entity_id_or_name

        self.remove_finished = False

        self.register_entities_event_handler(self.entity_remove_callback)

        self.remove_entity_request(entity_id_or_name, remove_aggregation)

        _timeout_s = timeout_ms / 1000.0

        _check_interval = 0.01

        _ended_ok = False

        entity_id = self.__get_entity_id(entity_id_or_name)  # Throws EntityNotDefinedException

        entity_name = self._osl_get_entity_name(entity_id).decode("utf-8")

        while _timeout_s >= 0:

            if self.remove_finished == False:

                _timeout_s -= _check_interval

                time.sleep(_check_interval)

            else:

                break

        return self.remove_finished

#########################################################################

    #Errors/Exceptions: EntityNotDefinedException

    def remove_aggregator_request(self, entity_id_or_name):

        self.__clear_error()

        entity_id = self.__get_entity_id(entity_id_or_name) # Throws EntityNotDefinedException

        retval = self._osl_remove_aggregator_request(ctypes.byref(self._err), entity_id)

        if (self._err.value == _ErrorType.ERROR_UNDEFINED_ENTITY.value or

                self._err.value == _ErrorType.ERROR_INACTIVE_ENTITY.value or

                self._err.value == _ErrorType.ERROR_DISABLED_WHILE_INITS.value):

            raise EntityNotDefinedException("entity doesn't exist in simulation")

        self._osl_send_pending_requests()

        assert retval == True, "Unknown error - " + self._err.value

#########################################################################

    #Errors/Exceptions: EntityNotDefinedException

    def set_aggregation_request(self, aggregator_id_or_name, aggregated_id_or_name):

        self.__clear_error()

        aggregatorId = self.__get_entity_id(aggregator_id_or_name) # Throws EntityNotDefinedException

        aggregatedId = self.__get_entity_id(aggregated_id_or_name) # Throws EntityNotDefinedException

        retval = self._osl_set_aggregation_request(ctypes.byref(self._err), aggregatorId, aggregatedId)

        if (self._err.value == _ErrorType.ERROR_UNDEFINED_ENTITY.value or

                self._err.value == _ErrorType.ERROR_INACTIVE_ENTITY.value or

                self._err.value == _ErrorType.ERROR_DISABLED_WHILE_INITS.value):

            raise EntityNotDefinedException("entity doesn't exist in simulation")

        self._osl_send_pending_requests()

        assert retval == True, "Unknown error - " + self._err.value

#########################################################################

    def register_entities_event_handler(self, callback):

        self.__clear_error()

        self.users_entities_callback = callback

        self.entities_callback = self.EntitiesFuncType(self.__entities_change_callback)

        self._osl_set_entities_event_handler(self.entities_callback)

#########################################################################

    def unregister_entities_event_handler(self):

        self.__clear_error()

        self.users_entities_callback = NULL

        self.entities_callback = self.EntitiesFuncType(NULL)

        self._osl_set_entities_event_handler(self.entities_callback)

#########################################################################

    def entity_id_to_unique_id(self, entity_id):

        self.__clear_error()

        retval = self._osl_entity_id_to_unique_id(entity_id)

        return retval

#########################################################################

    def get_platform_name(self, entity_type_id):

        self.__clear_error()

        retval = self._osl_get_platform_name(entity_type_id).decode("utf-8")

        return retval

#########################################################################

#=============================================================================

# SimState

#=============================================================================

 

#########################################################################

    def init(self, block_until_init_over_max_sec = 0, required_next_state = SimStateType.STATE_RUN):

        self.__clear_error()

        self._osl_set_simstate_request(SimStateType.STATE_INIT)

        self._osl_send_pending_requests()

        if not block_until_init_over_max_sec == 0:

            time.sleep(0.05) # postpone the checking in order to make the init state request take effect

            run_state_condition = lambda: self.get_sim_state() is required_next_state

            if not self.__timeout_on_goal_condition(run_state_condition, block_until_init_over_max_sec):

                raise TimeOutException("State didn't change to {} in the required timeout ({} seconds)".format(str(required_next_state), block_until_init_over_max_sec))

#########################################################################

    def run(self):

        self.__clear_error()

        self._osl_set_simstate_request(SimStateType.STATE_RUN)

        self._osl_send_pending_requests()

#########################################################################

    def stop(self):

        self.__clear_error()

        self._osl_set_simstate_request(SimStateType.STATE_STOP)

        self._osl_send_pending_requests()

#########################################################################

    def get_sim_time(self):

        self.__clear_error()

        sim_time = self._osl_get_simengine_time_msec()

        return sim_time

#########################################################################

    def get_sim_state(self):

        self.__clear_error()

        sim_state = self._osl_get_simstate()

        if sim_state == 1 or sim_state == 6:

            sim_state = 5 # Mapping STATE_RESET/STATE_FIRST_INIT to STATE_INIT

        if sim_state == 3:

            sim_state = 2 # Mapping STATE_FREEZE to STATE_STOP

        return SimStateType(sim_state)

#########################################################################

    def get_minor_period(self):

        self.__clear_error()

        minorPeriod = self._osl_get_minor_period()

        return minorPeriod

#########################################################################

    def register_simstate_event_handler(self, callback):

        self.__clear_error()

        self.users_simstate_callback = callback

        self.simstate_callback = self.SimStateFuncType(self.__sim_state_change_callback)

        self._osl_set_simstate_event_handler(self.simstate_callback)

#########################################################################

    def unregister_simstate_event_handler(self):

        self.__clear_error()

        self.users_simstate_callback = NULL

        self.simstate_callback = self.SimStateFuncType(NULL)

        self._osl_set_simstate_event_handler(self.simstate_callback)

#########################################################################

 

#=============================================================================

# Group and Stations

#=============================================================================

 

#########################################################################

    def get_station_names(self):

        self.__clear_error()

        amountOfStations = self._osl_get_amount_of_stations()

        stationNames = ['?']*amountOfStations

        for stationIdx in range(amountOfStations):

            stationNames[stationIdx] = self._osl_get_station_name_by_index(stationIdx).decode("utf-8")

        return stationNames

#########################################################################

    def get_station_sim_state(self, station_name):

        self.__clear_error()

        stationId = self._osl_get_station_name_id_name(station_name.encode())

        if stationId == -1:

            raise InvalidArgumentException("invalid station name, not in configuration.")

        sim_state = self._osl_get_station_simstate(stationId)

        if sim_state == 1 or sim_state == 6:

            sim_state = 5 # Mapping STATE_RESET/STATE_FIRST_INIT to STATE_INIT

        if sim_state == 3:

            sim_state = 2 # Mapping STATE_FREEZE to STATE_STOP

        return SimStateType(sim_state)

#########################################################################

    def get_workgroup_station_names(self):

        self.__clear_error()

        workgroup_name = self._osl_get_local_workgroup_name()

        amountOfStations = self._osl_get_amount_of_stations_in_workgroup(workgroup_name)

        stationNames = ['?']*amountOfStations

        for stationIdx in range(amountOfStations):

            stationNames[stationIdx] = self._osl_get_station_name_in_workgroup_by_index(workgroup_name, stationIdx).decode("utf-8")

        return stationNames

#########################################################################

    def get_own_station_name(self):

        self.__clear_error()

        stationId = self._osl_get_own_station_id()

        station_name = self._osl_get_station_name_by_id(stationId)

        return station_name.decode("utf-8")

#########################################################################

    def get_workgroup_name(self):

        self.__clear_error()

        workgroupName = self._osl_get_local_workgroup_name()

        return workgroupName.decode("utf-8")

#########################################################################

 

#=============================================================================

# Events

#=============================================================================

 

#########################################################################

    def inject_event(self, event_name, event_class_name, values, event_type = EventType.EVENT_GROUP, entity_name = '', source_station_name = ''):

        self.__clear_error()

 

        connected_to_sns = self._osl_is_connected_to_sns()

        result = False

        if connected_to_sns == True:

            event_id = self._osl_get_event_id(event_name.encode())

            eventClassId = self._osl_get_event_class_id(event_class_name.encode())

            if event_id >= 0 and eventClassId >= 0:

                amountOfValues = 0

                if values is not None:

                    amountOfValues = len(values)

                stationId = -1

                entity_id = -1

                if source_station_name is not None and source_station_name != '':

                    stationId = self._osl_get_station_name_id_name(source_station_name.encode())

                    if stationId == -1:

                        raise InvalidArgumentException("invalid station name, not in configuration.")

                if  entity_name is not None and entity_name != '':

                    entity_id = self._osl_get_entity_id(entity_name.encode())

                    if entity_id == -1:

                        raise InvalidArgumentException("invalid entity name.")

                if amountOfValues > 0:

                    arr = (ctypes.c_char_p * amountOfValues)()

                    for valueIdx in range(amountOfValues):

                        arr[valueIdx] = values[valueIdx].encode()

                    result = self._osl_inject_event_eng_request(stationId, event_id, eventClassId, entity_id, event_type, arr, amountOfValues)

                else:

                    result = self._osl_inject_event_eng_request(stationId, event_id, eventClassId, entity_id, event_type, None, 0)

            self._osl_send_pending_requests()

            if result == False:

                connected_to_sns = self._osl_is_connected_to_sns()

                if connected_to_sns == True:

                    raise InvalidArgumentException("")

        return result

#########################################################################

    def register_sim_engine_event_handler(self, callback, event_names_list):

        self.__clear_error()

        if self.events_thread_started == False:

            self._osl_start_events_monitoring()

            pollEventsThread = threading.Thread(target = poll_events_thread, args = (1, self), daemon = True)

            pollEventsThread.start()

            self.events_thread_started = True

        self._osl_clear_events_filter()

        filterSize = len(event_names_list)

        if filterSize > 0:

            for event_name in event_names_list:

                self._osl_add_events_filter(event_name.encode())

            self.users_sim_engine_event_callback = callback

            self.sim_engine_event_callback = self.SimEngineEventFuncType(self.__sim_engine_event_callback)

            self._osl_set_sim_engine_event_handler(self.sim_engine_event_callback)

        else:

            self._osl_clear_events_filter()

#########################################################################

    def unregister_sim_engine_event_handler(self, event_names_list):

        self.__clear_error()

        filterSize = len(event_names_list)

        if filterSize > 0:

            for event_name in event_names_list:

                self._osl_add_events_filter(event_name.encode())

            self.users_sim_engine_event_callback = NULL

            self.sim_engine_event_callback = self.SimEngineEventFuncType(NULL)

            self._osl_set_sim_engine_event_handler(self.sim_engine_event_callback)

        else:

            self._osl_clear_events_filter()

#########################################################################

    def get_event_names(self):

        self.__clear_error()

        amountOfEvents = self._osl_get_amount_of_events()

        eventNames = ['?']*amountOfEvents

        for event_id in range(amountOfEvents):

            eventNames[event_id] = self._osl_get_event_name(event_id).decode("utf-8")

        return eventNames

#########################################################################

    def get_event_class_names(self):

        self.__clear_error()

        amountOfEventClasses = self._osl_get_amount_of_event_classes()

        eventClassNames = ['?']*amountOfEventClasses

        for eventClassId in range(amountOfEventClasses):

            eventClassNames[eventClassId] = self._osl_get_event_class_name(eventClassId).decode("utf-8")

        return eventClassNames

#########################################################################

 

#=============================================================================

# Recorder

#=============================================================================

 

#########################################################################

    def start_recording_request(self, session_name):

        self.__clear_error()

        result = self._osl_start_recording_request(ctypes.byref(self._err), session_name.encode(), 0)

        self._osl_send_pending_requests()

        return result

#########################################################################

    def start_playback_request(self, session_name):

        self.__clear_error()

        result = self._osl_start_playback_request(ctypes.byref(self._err), session_name.encode())

        self._osl_send_pending_requests()

        return result

#########################################################################

    def jump_to_time_request(self, jump_to_time_msec):

        self.__clear_error()

        result = self._osl_jump_to_time_request(ctypes.byref(self._err), jump_to_time_msec)

        self._osl_send_pending_requests()

        return result

#########################################################################

    def play_forward_request(self, rate):

        self.__clear_error()

        result = self._osl_play_forward_request(ctypes.byref(self._err), rate)

        self._osl_send_pending_requests()

        return result

#########################################################################

    def play_backward_request(self, rate):

        self.__clear_error()

        result = self._osl_play_backward_request(ctypes.byref(self._err), rate)

        self._osl_send_pending_requests()

        return result

#########################################################################

    def close_session_request(self):

        self.__clear_error()

        result = self._osl_close_session_request(ctypes.byref(self._err))

        self._osl_send_pending_requests()

        return result

#########################################################################

    def save_snappoint_request(self, snappoint_id):

        self.__clear_error()

        result = self._osl_save_snappoint_request(ctypes.byref(self._err), snappoint_id, None)

        self._osl_send_pending_requests()

        return result

#########################################################################

    def load_snappoint_request(self, snappoint_id):

        self.__clear_error()

        result = self._osl_load_snappoint_request(ctypes.byref(self._err), snappoint_id)

        self._osl_send_pending_requests()

        return result

#########################################################################

    def get_recording_state(self):

        self.__clear_error()

        recordingState = RecordingState()

        sessionModeId = self._osl_get_session_mode()

        recordingState.session_mode = self.__session_mode_id_to_string(sessionModeId)

        recordingState.recording_time_ms = self._osl_get_recording_time_ms()

        return recordingState

#########################################################################

    def get_last_recordeing_command_error(self):

        self.__clear_error()

        message = self._osl_get_last_recorder_command_message().decode('utf-8')

        return message

#########################################################################

 

#=============================================================================

# Session Store / Load

#=============================================================================

 

    def store_current_session_configuration(self, path):

        self.__clear_error()

        if not self._osl_store_current_session_configuration(path.encode()):

            error = self._osl_get_error().decode('utf-8')

            raise Exception("Failed to store current session configuration.", error)

 

    def load_session_configuration(self, path):

        self.__clear_error()

        if not self._osl_load_session_configuration(path.encode()):

            error = self._osl_get_error().decode('utf-8')

            raise Exception("Failed to load session configuration.", error)

 

#=============================================================================

# Models

#=============================================================================

 

    def send_station_model_message(self, station_name, model_name, buffer):

        self.__clear_error()

        if not self._osl_send_station_model_message(station_name.encode(), model_name.encode(), buffer.encode()):

            error = self._osl_get_error().decode('utf-8')

            raise ModelMessageSendFailureException("Failed to send station model message.", error)

 

    def send_station_model_message_and_wait_for_response_non_blocking(self, station_name, model_name, buffer, callback, timeout_sec = -1):

        self.__clear_error()

        self.users_station_message_respond_callback = callback

        self.station_message_respond_callback = self.StationMessageRespondFuncType(self.__station_message_respond_callback)

        success = self._osl_send_station_model_message_and_wait_for_response(station_name.encode(), model_name.encode(), buffer.encode(),

        self.station_message_respond_callback, timeout_sec)

        if not success:

            error = self._osl_get_error().decode('utf-8')

            raise ModelMessageSendFailureException("Failed to send station model message and wait for response.", error)

 

    def send_station_model_message_and_wait_for_response_blocking(self, station_name, model_name, buffer, timeout_sec = -1):

        self.__clear_error()

        self.send_station_model_message_and_wait_for_response_non_blocking(station_name, model_name, buffer, self.station_message_respond_callback_internal, timeout_sec)

        buffer = self.queue_station_message_respond_callback.get()

        return buffer

 

    def set_mmi_socket_sync_mode(self, enable, cycle_rate):

        self.__clear_error()

        self._osl_set_mmi_socket_sync_mode(enable, cycle_rate)

 

#=============================================================================

# Others

#=============================================================================

 

    def set_best_effort_mode(enable = True):

        simWrapper.best_effort = enable

 

#=============================================================================

# Private

#=============================================================================

 

#########################################################################

    def __mode_none():

        return "None"

 

    def __mode_simulation():

        return "Simulation"

 

    def __mode_recording():

        return "Recording"

 

    def __mode_playback():

        return "Playback"

 

    __switcher_session_mode = {0: __mode_none,

                                1: __mode_recording,

                                2: __mode_playback,

                                3: __mode_simulation}

 

    def __session_mode_id_to_string(self, argument):

        func = self.__switcher_session_mode.get(argument, "nothing")

        return func()

#########################################################################

    def __timeout_on_goal_condition(self, goal_condition, seconds, sleep_interval = 0.05):

        while not goal_condition():

            if seconds <= 0:

                return False

            time.sleep(sleep_interval)

            seconds -= sleep_interval

        return True

 

#########################################################################

    def __timeout_element_condition(self, element, unit, condition, seconds, sleep_interval = 0.05):

        self.__clear_error()

        retval = None

        element_valid, element_reg_id = self.__register_element(element)

        if not element_valid:

            self._err.value = _ErrorType.ERROR_INVALID_ELEMENT.value

            raise ElementNotDefinedException("element doesn't exist in simulation, element = " + element)

        eng_format = 0

        time_remained = seconds

        while time_remained >= 0:

            time_before = time.time()

            if not self._osl_get_element_value_for_scripts(

                    ctypes.byref(self._err), element_reg_id, self._val, self._ELEMENT_BUFFER_SIZE, unit.encode(),

                    eng_format, int(time_remained * 1000.0)):

                if self._err.value == _ErrorType.ERROR_NOT_SAMPLED.value:

                    # Sampling timeout

                    return False

                # else - some kind of error

                if self._err.value == _ErrorType.ERROR_NOT_SAMPLED.value:

                    raise ElementNotDefinedException("element doesn't exist in simulation, element = " + element)

                raise Exception("internal error occurred ({}) while trying to get value of element {}".format(self._err.value, element))

            # check the value

            value = self._val.value.decode()

            if condition(value):

                return True

            # else - keep waiting

            time_after = time.time()

            time_elapsed = time_after - time_before

            if time_elapsed < sleep_interval:

                time.sleep(sleep_interval - time_elapsed)

                time_elapsed = sleep_interval

            time_remained -= time_elapsed

        # Timeout reached

        return False

 

#########################################################################

    def __wait_for_connection(self, seconds):

        time_remained = seconds

        sleep_interval = 0.2

        print('Waiting for sns/shmem connection!')

        while time_remained >= 0:

            self._osl_server_update()

            time_before = time.time()

            connected_to_sns = self._osl_is_connected_to_sns()

            connected_to_shmem = self._osl_is_received_messages_from_rt()

            if (connected_to_sns and connected_to_shmem) == True:

                print('Connected to sns/shmem, took ', (seconds - time_remained))

                return True

            # else - keep waiting

            time_after = time.time()

            time_elapsed = time_after - time_before

            if time_elapsed < sleep_interval:

                time.sleep(sleep_interval - time_elapsed)

                time_elapsed = sleep_interval

            time_remained -= time_elapsed

        print('Failed to connected to sns/shmem')

 

#########################################################################

    def __register_element(self, element):

        element_valid = False

        with self._registered_elements_lock:

            element_reg_id = self._registered_elements.get(element)

            if element_reg_id is None:

                is_valid, element_block, element_name = self.__parse_element(element)

                if is_valid:

                    element_reg_id = self._osl_register_element(element_block.encode(), element_name.encode(), True, True)

                    if element_reg_id > -1:

                        self._registered_elements[element] = element_reg_id

                        self._reveresed_registered_elements[element_reg_id] = element

                        element_valid = True

            else:

                element_valid = True

        return element_valid, element_reg_id

#########################################################################

    def __parse_element(self, element):

        element_lst = element.split('.')

        element_valid = False

        element_block = None

        element_name = None

        if len(element_lst) > 3:

            element_block = '.'.join(element.split('.')[:3])

            element_name = '.'.join(element.split('.')[3:])

            element_valid = True

        return element_valid, element_block, element_name

#########################################################################

    def __clear_error(self):

        self._err.value = _ErrorType.ERROR_NONE.value

#########################################################################

    def __unregister_all_elements(self):

        self.__clear_error()

        with self._registered_elements_lock:

            for element_name, element_reg_id in self._registered_elements.items():

                if element_reg_id is not None and element_reg_id >= 0:

                    self._osl_unregister_element(element_reg_id)

        self._osl_send_pending_requests()

#########################################################################

    def poll_events(self):

        self._osl_poll_events()

#########################################################################

    def __sim_state_change_callback(self, sim_state):

        simStateType = SimStateType(sim_state)

        self.users_simstate_callback(simStateType)

#########################################################################

    def __sim_engine_event_callback(self, event_index, sim_time, frame_counter, event_id, event_name, class_id, class_name, entity_id, source_station_id, type, event_data_buffer, event_data_buffer_length):

        eventNameStr = event_name.decode("utf-8")

        classNameStr = class_name.decode("utf-8")

        event_type = EventType(type)

        entity_name = ''

        if entity_id > 0:

            entity_name = self._osl_get_entity_name(entity_id).decode("utf-8")

        station_name = self._osl_get_station_name_by_id(source_station_id).decode("utf-8")

        amountOfElements = self._osl_get_amount_of_event_elements(class_id)

        values = [None] * amountOfElements

        for elementIdx in range(amountOfElements):

            values[elementIdx] = self._osl_get_event_element_value(class_id, elementIdx, event_data_buffer, event_data_buffer_length).decode("utf-8")

        self.users_sim_engine_event_callback(sim_time, frame_counter, eventNameStr, classNameStr, event_type, entity_name, station_name, values)

#########################################################################

    def __entities_change_callback(self, command, entity_id, entity_full_name, entity_type_name):

        entityCommandType = EntityCommandType(command)

        entityFullNameStr = entity_full_name.decode("utf-8")

        entityTypeNameStr = entity_type_name.decode("utf-8")

        self.users_entities_callback(entityCommandType, entity_id, entityFullNameStr, entityTypeNameStr)

#########################################################################

    def __get_entity_id(self, entity_id_or_name):

        entity_id = entity_id_or_name

        isName = isinstance(entity_id_or_name, str)

        if isName == True:

            entity_id = self.get_entity_id(entity_id_or_name)

        if entity_id < 0:

            raise EntityNotDefinedException("entity doesn't exist in simulation, entity = " + entity_id_or_name)

        return entity_id

#########################################################################

    def __element_registration_callback(self, registartion_id, registration_event_type):

        if registration_event_type == ElementRegistrationEventType.ELEMENT_UNREGISTERED.value:

            with self._registered_elements_lock:

                element = self._reveresed_registered_elements[registartion_id]

                try:

                    self._reveresed_registered_elements.pop(registartion_id)

                except Exception as e:

                    pass

                try:

                    self._registered_elements.pop(element)

                except Exception as e:

                    pass

#########################################################################

    def __register_element_registration_event_handler(self):

        self.ref_element_registration = self.ElementRegistrationFuncType(self.__element_registration_callback)

        self._osl_set_element_registration_event_handler(self.ref_element_registration)

#########################################################################

    def __station_message_respond_callback(self, buffer):

        userBuffer = buffer.decode("utf-8")

        self.users_station_message_respond_callback(userBuffer)

#########################################################################

    queue_station_message_respond_callback = queue.Queue()

 

    def station_message_respond_callback_internal(self, buffer):

        self.queue_station_message_respond_callback.put(buffer)

#########################################################################

    def entity_remove_callback(self, command, entity_id, name, type):

        if command == EntityCommandType.CMD_DEL and (entity_id == self.removed_entity_id_or_name or name == self.removed_entity_id_or_name):

            self.remove_finished = True

            self.unregister_entities_event_handler()

#########################################################################

 