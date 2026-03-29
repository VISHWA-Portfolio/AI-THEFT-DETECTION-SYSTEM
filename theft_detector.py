import os
import sys
import cv2  # type: ignore
import time
import threading
try:
    import pywhatkit  # type: ignore
except ImportError:
    pywhatkit = None
from ultralytics import YOLO  # type: ignore
from datetime import datetime
from typing import List, Any, Dict, Set

# --- CONFIGURATION ---
TARGET_PHONE = "your mobile number"
MISSING_TIME_THRESH = 5.0  # Increased to 5s to prevent YOLO amnesia false alarms
INTERACTION_PADDING = 100   # Expanded to 100px so hand hovers definitively protect items

is_sending_alert = False

def send_whatsapp_alert(image_path: str, caption: str) -> None:
    global is_sending_alert
    if is_sending_alert:
        print("THREAD SHIELD: Already actively typing an alert! Ignoring simultaneous theft to prevent mouse crashing.")
        return
        
    is_sending_alert = True
    print(f"THREAD: Sending WhatsApp alert to {TARGET_PHONE}... (Hands off the keyboard!)")
    try:
        import webbrowser
        import pyautogui # type: ignore
        import subprocess
        import time

        # We inject a direct URL to open the specific chat.
        url = f"https://web.whatsapp.com/send?phone={TARGET_PHONE.replace('+', '')}"
        webbrowser.open(url)
        
        # We wait 20 seconds for the browser to launch, load Whatsapp Web, and open the chat
        print("THREAD: Waiting 20 seconds for WhatsApp Web to load...")
        time.sleep(20)
        
        print("THREAD: Copying image to clipboard...")
        # A 100% reliable native Windows Powershell command to copy an image file to the clipboard directly
        cmd = f'powershell -command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Clipboard]::SetImage([System.Drawing.Image]::FromFile(\'{image_path}\'))"'
        subprocess.run(cmd, shell=True, check=True)
        
        # Give the system 1 second to register the clipboard change
        time.sleep(1)
        
        print("THREAD: Pasting image into WhatsApp...")
        # Simulate pressing Ctrl+V
        pyautogui.hotkey('ctrl', 'v')
        
        # Wait 3 seconds for the Image Preview / Caption UI to load
        time.sleep(3)
        
        print("THREAD: Typing message and sending...")
        # Type the alert caption slowly to ensure it doesn't get messed up 
        pyautogui.write(caption, interval=0.01)
        time.sleep(2)
        
        # Finally explicitly execute the Send command
        # Some OS configurations require pressing 'enter' twice when an image is attached
        pyautogui.press('enter')
        time.sleep(1)
        pyautogui.press('enter')
        print("THREAD: WhatsApp alert sent successfully!")
        time.sleep(2)
        
    except Exception as e:
        import traceback
        print(f"THREAD ERROR: Failed to send WhatsApp alert:")
        traceback.print_exc()
    finally:
        is_sending_alert = False

def check_overlap(box1: Any, box2: Any) -> bool:
    # Guaranteed geometry collision check to register every physical touch cleanly without float math drop-offs
    x_left = max(box1[0], box2[0])
    y_top = max(box1[1], box2[1])
    x_right = min(box1[2], box2[2])
    y_bottom = min(box1[3], box2[3])
    return (x_right >= x_left) and (y_bottom >= y_top)

def draw_hud(frame: Any, state: str) -> None:
    h, w, _ = frame.shape
    cv2.rectangle(frame, (0, 0), (w, 60), (0, 0, 0), -1)
    cv2.putText(frame, "AI INTERACTION + STOLEN LOGIC (Day 4 Base)", (20, 35), 
                cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 255, 0), 2)
    
    color = (0, 255, 0)
    if state == "INTERACTION DETECTED!": color = (0, 255, 255)
    elif "STOLEN!!" in state: color = (0, 0, 255)
    
    cv2.putText(frame, f"STATUS: {state}", (20, h - 20), cv2.FONT_HERSHEY_DUPLEX, 0.8, color, 2)

def main():
    os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"

    cap: Any = None
    found_cam = False
    for backend in [None, cv2.CAP_DSHOW, cv2.CAP_MSMF]:
        for idx in [0, 1, 2]:
            backend_label = "Default" if backend is None else ("DSHOW" if backend == cv2.CAP_DSHOW else "MSMF")
            print(f"Attempting camera index {idx} with {backend_label} backend...")
            
            if backend is None:
                cap = cv2.VideoCapture(idx)
            else:
                cap = cv2.VideoCapture(idx, backend)
            
            if cap is not None and cap.isOpened():
                # Removing strict 4K bindings to prevent hardware pixel breaking/compression defects
                cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)

                ret, _ = cap.read()
                if ret:
                    print(f"SUCCESS: Camera {idx} with {backend_label} opened and reading.")
                    found_cam = True
                    break
                cap.release()
            cap = None
        if found_cam: break

    if cap is None:
        print("WARNING: Live camera not found. Trying fallback video...")
        if os.path.exists("../sample_cctv.mp4"): cap = cv2.VideoCapture("../sample_cctv.mp4")
        
    if cap is not None:
        if not cap.isOpened():
            print("ERROR: Video source opened but is not functional. Exiting.")
            sys.exit(1)
    else:
        print("ERROR: Could not initialize any video source. Exiting.")
        sys.exit(1)

    assert cap is not None
    time.sleep(1) 
    for _ in range(10):
        ret, _ = cap.read()
        if ret: break
        time.sleep(0.1)

    model = YOLO("yolov8s.pt")
    
    print("DAY 4 + STOLEN: Engine Active.")
    print("STEP 1: Select the INTERACTION ZONE (Shelf) with your mouse.")
    print("STEP 2: Press ENTER or SPACE to confirm, or 'c' to cancel.")

    ret, init_frame = cap.read()
    if not ret or init_frame is None:
        print("ERROR: Could not grab initial frame for ROI selection.")
        sys.exit(1)
    
    init_frame = cv2.flip(init_frame, 1)
    roi_display = cv2.resize(init_frame, (1024, 768))
    
    roi = cv2.selectROI("Select Interaction Zone", roi_display, fromCenter=False, showCrosshair=True)
    cv2.destroyWindow("Select Interaction Zone")
    
    if roi == (0, 0, 0, 0):
        roi = (0, 0, 1024, 768)
        print("INFO: No ROI selected. Monitoring full frame.")
    else:
        print(f"INFO: Interaction Zone Selected: {roi}")

    # Lowered varThreshold from 250 -> 50 so it correctly registers human hands again
    fgbg = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)
    
    tracked_items: Dict[int, Any] = {}
    missing_items: Dict[int, float] = {}
    stolen_records: Set[int] = set()

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                max_retries = 30
                retry_count = 0
                while not ret and retry_count < max_retries:
                    time.sleep(0.1)
                    ret, frame = cap.read()
                    retry_count += 1
                if not ret: 
                    print("ERROR: Camera feed lost.")
                    break
                
            frame = cv2.flip(frame, 1)
            frame = cv2.resize(frame, (1024, 768))
            display_frame = frame.copy()
            
            rx1_raw, ry1_raw, rw_raw, rh_raw = roi
            rx1, ry1, rw, rh = int(rx1_raw), int(ry1_raw), int(rw_raw), int(rh_raw)
            rx2, ry2 = rx1 + rw, ry1 + rh
            cv2.rectangle(display_frame, (rx1, ry1), (rx2, ry2), (255, 255, 255), 1)
            cv2.putText(display_frame, "INTERACTION ZONE", (rx1, ry1-5), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

            results = model.track(frame, conf=0.35, persist=True, verbose=False, imgsz=640)
            
            fgmask = fgbg.apply(frame)
            _, thresh = cv2.threshold(fgmask, 200, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            motion_boxes: List[Any] = []
            for cnt in contours:
                if cv2.contourArea(cnt) > 500: # Lowered to securely capture small hands/fingers
                    mx_raw, my_raw, mw_raw, mh_raw = cv2.boundingRect(cnt)
                    mx, my, mw, mh = int(mx_raw), int(my_raw), int(mw_raw), int(mh_raw)
                    motion_boxes.append((mx, my, mx+mw, my+mh))
                    
                    # Highlight Hand Movement so you can visibly SECURE your motion is working
                    cv2.rectangle(display_frame, (mx, my), (mx+mw, my+mh), (200, 200, 200), 1)
            
            any_interaction = False
            system_state = "SCANNING"
            seen_tids: Set[int] = set()

            if results and results[0].boxes is not None:
                system_state = "SECURE"
                result = results[0]
                boxes = result.boxes.xyxy.cpu().numpy()
                class_ids = result.boxes.cls.int().cpu().numpy()
                
                res_ids = getattr(result.boxes, 'id', None)
                res_temp = res_ids.int().cpu().tolist() if res_ids is not None else []
                id_list = list(res_temp) # type: ignore
                
                person_boxes: List[Any] = []
                for i, b_raw in enumerate(boxes.tolist()):
                    b: Any = b_raw
                    cid_raw = class_ids.tolist()[i]
                    cid = int(cid_raw) if cid_raw is not None else 0
                    
                    cname = str(model.names[cid])
                    if cname == 'person':
                        person_boxes.append(b)
                        cx, cy = (int(b[0])+int(b[2]))//2, (int(b[1])+int(b[3]))//2
                        p_color = (255, 100, 0) if (rx1 <= cx <= rx2 and ry1 <= cy <= ry2) else (180, 180, 180)
                        cv2.rectangle(display_frame, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), p_color, 2)

                for i, b_raw in enumerate(boxes.tolist()):
                    b: Any = b_raw
                    cid_raw = class_ids.tolist()[i]
                    cid = int(cid_raw) if cid_raw is not None else 0
                    
                    tid = None
                    if i < len(id_list):
                        tid_raw = id_list[i] # type: ignore
                        tid = int(tid_raw) if tid_raw is not None else None
                        
                    cname = str(model.names[cid])
                    if cname != 'person':
                        cx, cy = (int(b[0])+int(b[2]))//2, (int(b[1])+int(b[3]))//2
                        in_roi = (rx1 <= cx <= rx2) and (ry1 <= cy <= ry2)

                        if tid is not None:
                            valid_tid: int = int(tid)
                            # Register item securely if detected ANYWHERE in frame, preventing false missing alarms
                            seen_tids.add(valid_tid)
                            
                            if in_roi:
                                if valid_tid not in tracked_items:
                                    tracked_items.update({valid_tid: {"box": b, "class": cname}}) 
                                else:
                                    t_item = tracked_items.get(valid_tid)
                                    if isinstance(t_item, dict):
                                        t_item.update({"box": b}) 

                                if valid_tid in missing_items:
                                    missing_items.pop(valid_tid, None)
                                if valid_tid in stolen_records:
                                    stolen_records.discard(valid_tid)

                        touched = False
                        if in_roi:
                            pad_b = [b[0]-INTERACTION_PADDING, b[1]-INTERACTION_PADDING, 
                                     b[2]+INTERACTION_PADDING, b[3]+INTERACTION_PADDING]
                            for pb in person_boxes + motion_boxes:
                                if check_overlap(pad_b, pb):
                                    touched = True
                                    any_interaction = True
                                    break
                        
                        color = (0, 255, 255) if touched else ((0, 255, 0) if in_roi else (128, 128, 128))
                        if touched: 
                            cv2.rectangle(display_frame, (int(b[0])-5, int(b[1])-5), (int(b[2])+5, int(b[3])+5), (0, 0, 255), 3)
                        
                        cv2.rectangle(display_frame, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), color, 2)
                        
                        label_suffix = ""
                        if not in_roi: label_suffix = " (IGNORED)"
                        elif in_roi and not touched: label_suffix = " (MONITORED)"
                        elif touched: label_suffix = " (INTERACTING)"
                            
                        label = f"{cname.upper()}"
                        if tid is not None:
                            if tid in tracked_items: label += " (STOCKED)"
                            else: label += f" ID:{tid}"
                        else:
                            label += " (NEW)"
                        
                        label += label_suffix
                        cv2.putText(display_frame, label, (int(b[0]), int(b[1] - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

            # --- STOLEN LOGIC (Added to Day 4) ---
            now_time = float(time.time())
            for tid_key in list(tracked_items.keys()):
                valid_tid_key: int = int(tid_key)
                if valid_tid_key not in seen_tids:
                    val = missing_items.get(valid_tid_key)
                    
                    # INTERACTION VS STOLEN OPTIMIZATION:
                    # If the item's last known position is actively covered by a hand/person,
                    # it is 'Occluded' (Interaction), not 'Missing' (Stolen). Reset the theft timer!
                    occluded = False
                    item_data = tracked_items.get(valid_tid_key)
                    b = None if not isinstance(item_data, dict) else item_data.get("box")
                    
                    if b is not None and isinstance(b, (list, tuple)) and len(b) >= 4:
                        pad_b = [b[0]-INTERACTION_PADDING, b[1]-INTERACTION_PADDING, 
                                 b[2]+INTERACTION_PADDING, b[3]+INTERACTION_PADDING]
                        for pb in person_boxes + motion_boxes:
                            if check_overlap(pad_b, pb):
                                occluded = True
                                any_interaction = True
                                break

                    if occluded:
                        missing_items.update({valid_tid_key: now_time}) # Reset timer while handling
                        # Draw safe ghost box to indicate occlusion tracking
                        if b is not None:
                            cv2.rectangle(display_frame, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (0, 255, 255), 2)
                            cv2.putText(display_frame, f"OCCLUDED: ID {valid_tid_key}", (int(b[0]), int(b[1] - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                    else:
                        if val is None:
                            missing_items.update({valid_tid_key: now_time})
                        elif now_time - float(val) > MISSING_TIME_THRESH:
                            # Stolen!
                            if valid_tid_key not in stolen_records:
                                stolen_records.add(valid_tid_key)
                                
                                import os as _os
                                alert_img_path = _os.path.abspath(f"stolen_alert_{valid_tid_key}.jpg")
                                cv2.imwrite(alert_img_path, display_frame)
                                print(f"*** ALERT: Capture saved to {alert_img_path} ***")
                                
                                caption = f"🚨 AI THEFT ALERT 🚨\nItem ID {valid_tid_key} has been stolen from the monitoring zone at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}!"
                                threading.Thread(target=send_whatsapp_alert, args=(alert_img_path, caption), daemon=True).start()
                            
                            # Draw ghost box of stolen item
                            if b is not None:
                                cv2.rectangle(display_frame, (int(b[0]), int(b[1])), (int(b[2]), int(b[3])), (0, 0, 255), 3)
                                cv2.putText(display_frame, f"STOLEN: ID {valid_tid_key}", (int(b[0]), int(b[1] - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)


            if len(stolen_records) > 0:
                system_state = f"STOLEN!! ({len(stolen_records)} missing)"

            system_state = system_state if "STOLEN!!" in system_state else ("INTERACTION DETECTED!" if any_interaction else ("SCANNING" if system_state == "SCANNING" else "SECURE"))
            draw_hud(display_frame, system_state)
            
            cv2.imshow('AI Interaction Tracker - Day 4 + Stolen', display_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'): break
            if cv2.waitKey(1) & 0xFF == ord('c'):
                tracked_items.clear()
                missing_items.clear()
                stolen_records.clear()
    except Exception as e:
        import traceback
        print("CRITICAL CRASH:")
        traceback.print_exc()
        input("Press Enter to exit...")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
