import ctypes
import os
import sys
import time

"""
Простой "пир" для wirtrans.dll.

Идея:
- эту папку (wirtrans_usb) копируем на флешку;
- кладём сюда же собранную wirtrans.dll (x64, если Python 64-битный);
- на другом компьютере запускаем:  python run_peer.py

Этот скрипт:
- загружает wirtrans.dll;
- вызывает WT_Init + WT_StartMDNS;
- остаётся висеть, периодически обмениваясь mDNS-пакетами с другими такими же пирам.
"""

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DLL_PATH = os.path.join(BASE_DIR, "wirtrans.dll")


class WT_DeviceInfo(ctypes.Structure):
    _fields_ = [
        ("source", ctypes.c_int),
        ("ip", ctypes.c_char * 16),
        ("port", ctypes.c_uint16),
        ("note", ctypes.c_char * 128),
    ]


CB = ctypes.WINFUNCTYPE(None, ctypes.POINTER(WT_DeviceInfo), ctypes.c_void_p)


def main() -> int:
    print("=======================================")
    print(" wirtrans PEER (USB demo)")
    print("=======================================")
    print("Python :", sys.version)
    print("DLL    :", DLL_PATH)
    print()

    if not os.path.exists(DLL_PATH):
        print("ОШИБКА: не найден wirtrans.dll рядом с run_peer.py")
        print("Скопируй сюда собранную DLL (x64/Debug или Release) и запусти снова.")
        return 1

    lib = ctypes.WinDLL(DLL_PATH)

    lib.WT_Init.argtypes = []
    lib.WT_Init.restype = ctypes.c_int
    lib.WT_Shutdown.argtypes = []
    lib.WT_Shutdown.restype = None

    lib.WT_SetLogEnabled.argtypes = [ctypes.c_int]
    lib.WT_SetLogEnabled.restype = None

    lib.WT_SetDeviceFoundCallback.argtypes = [CB, ctypes.c_void_p]
    lib.WT_SetDeviceFoundCallback.restype = None

    lib.WT_StartMDNS.argtypes = []
    lib.WT_StartMDNS.restype = ctypes.c_int
    lib.WT_StopMDNS.argtypes = []
    lib.WT_StopMDNS.restype = None

    @CB
    def on_device(info_ptr, user_ptr):
        info = info_ptr.contents
        ip = info.ip.decode("ascii", errors="ignore").rstrip("\x00")
        note = info.note.decode("utf-8", errors="ignore").rstrip("\x00")
        src = "MDNS" if info.source == 1 else "SCAN" if info.source == 2 else str(info.source)
        print(f"[CB] src={src} ip={ip} note={note}")

    if lib.WT_Init() == 0:
        print("WT_Init failed")
        return 1

    cb_ref = on_device  # держим ссылку, чтобы callback не собрал GC
    lib.WT_SetDeviceFoundCallback(cb_ref, None)
    lib.WT_SetLogEnabled(1)

    if not lib.WT_StartMDNS():
        print("WT_StartMDNS failed (проверь порт 5353 и firewall)")
        lib.WT_Shutdown()
        return 1

    print("Пир запущен. Этот компьютер теперь виден другим экземплярам wirtrans по mDNS.")
    print("Оставь окно открытым. Для выхода нажми Ctrl+C.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nОстанавливаемся...")

    lib.WT_StopMDNS()
    lib.WT_Shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

