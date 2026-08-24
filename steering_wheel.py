import cv2
import mediapipe as mp
import numpy as np
import math
import time
import platform
import vgamepad as vg


# ============================================================
# CAMERA
# ============================================================

CAMERA_INDEX = 0


# ============================================================
# STEERING SENSITIVITY
# KEEPING YOUR WORKING SETTINGS
# ============================================================

DEAD_ZONE_DEG = 5
RELEASE_ZONE_DEG = 3
MAX_STEER_DEG = 32
STEERING_CURVE = 0.70

FLIP_CAMERA = True
SHOW_ANGLE = True

MIN_DETECTION_CONF = 0.7
MIN_TRACKING_CONF = 0.5

GRACE_FRAMES = 8
OPEN_FINGER_THRESH = 3


# ============================================================
# THROTTLE / BRAKE
# ============================================================

# Xbox triggers use 0.0 -> 1.0
FULL_THROTTLE = 1.0
FULL_BRAKE = 1.0


# ============================================================
# DISPLAY COLORS
# ============================================================

CLR_WHEEL = (80, 200, 255)
CLR_LEFT = (60, 120, 255)
CLR_RIGHT = (50, 220, 140)
CLR_NEUTRAL = (200, 200, 200)
CLR_TEXT = (255, 255, 255)
CLR_ACCENT = (0, 180, 255)
CLR_HAND_L = (255, 130, 60)
CLR_HAND_R = (60, 230, 130)
CLR_ACCEL = (50, 220, 100)
CLR_BRAKE = (0, 60, 255)


# ============================================================
# MEDIAPIPE
# ============================================================

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils


# ============================================================
# VIRTUAL XBOX CONTROLLER
# ============================================================

print("[INFO] Creating virtual Xbox controller...")

gamepad = vg.VX360Gamepad()

print("[OK] Virtual Xbox controller created.")


# ============================================================
# OPEN HAND DETECTION
# ============================================================

def is_open_hand(hand_landmarks):

    finger_tips = [
        8,
        12,
        16,
        20
    ]

    finger_pips = [
        6,
        10,
        14,
        18
    ]

    extended = sum(
        1
        for tip, pip in zip(
            finger_tips,
            finger_pips
        )
        if (
            hand_landmarks.landmark[tip].y
            <
            hand_landmarks.landmark[pip].y
        )
    )

    return (
        extended >= OPEN_FINGER_THRESH
    )


# ============================================================
# STEERING CONTROLLER
# ============================================================

class SteeringController:

    def __init__(self):

        self.angle_history = []

        self.HISTORY_LEN = 3

    # --------------------------------------------------------
    # SMOOTH ANGLE
    # --------------------------------------------------------

    def smooth_angle(self, raw_angle):

        self.angle_history.append(
            raw_angle
        )

        if (
            len(self.angle_history)
            >
            self.HISTORY_LEN
        ):

            self.angle_history.pop(0)

        return float(
            np.mean(
                self.angle_history
            )
        )

    # --------------------------------------------------------
    # RELEASE EVERYTHING
    # --------------------------------------------------------

    def release_all(self):

        # Steering center
        gamepad.left_joystick_float(
            x_value_float=0.0,
            y_value_float=0.0
        )

        # Release triggers
        gamepad.right_trigger_float(
            0.0
        )

        gamepad.left_trigger_float(
            0.0
        )

        # Release digital buttons
        gamepad.release_button(
            vg.XUSB_BUTTON.XUSB_GAMEPAD_A
        )

        gamepad.release_button(
            vg.XUSB_BUTTON.XUSB_GAMEPAD_B
        )

        gamepad.release_button(
            vg.XUSB_BUTTON.XUSB_GAMEPAD_X
        )

        gamepad.release_button(
            vg.XUSB_BUTTON.XUSB_GAMEPAD_Y
        )

        gamepad.update()

        self.angle_history.clear()

    # --------------------------------------------------------
    # STEERING
    # --------------------------------------------------------

    def update_steer(
        self,
        left_wrist,
        right_wrist
    ):

        dx = (
            right_wrist[0]
            -
            left_wrist[0]
        )

        dy = (
            right_wrist[1]
            -
            left_wrist[1]
        )

        raw_angle_rad = math.atan2(
            dy,
            dx
        )

        raw_angle_deg = math.degrees(
            raw_angle_rad
        )

        angle = self.smooth_angle(
            raw_angle_deg
        )

        # ====================================================
        # DEAD ZONE
        # ====================================================

        if (
            abs(angle)
            <=
            DEAD_ZONE_DEG
        ):

            steering = 0.0

        else:

            magnitude = (
                abs(angle)
                -
                DEAD_ZONE_DEG
            ) / (
                MAX_STEER_DEG
                -
                DEAD_ZONE_DEG
            )

            magnitude = max(
                0.0,
                min(
                    1.0,
                    magnitude
                )
            )

            # Non-linear sensitivity
            magnitude = (
                magnitude
                **
                STEERING_CURVE
            )

            if angle > 0:

                steering = magnitude

            else:

                steering = -magnitude

        # ====================================================
        # SEND ANALOG STEERING
        # ====================================================

        gamepad.left_joystick_float(
            x_value_float=steering,
            y_value_float=0.0
        )

        # ====================================================
        # DIRECTION FOR HUD
        # ====================================================

        if steering < -0.03:

            direction = "LEFT"

        elif steering > 0.03:

            direction = "RIGHT"

        else:

            direction = "STRAIGHT"

        strength = abs(
            steering
        )

        return (
            angle,
            direction,
            strength
        )

    # --------------------------------------------------------
    # THROTTLE / BRAKE
    # --------------------------------------------------------

    def update_throttle(
        self,
        left_open,
        right_open
    ):

        # ====================================================
        # CLEAR OLD TRIGGER VALUES
        # ====================================================

        gamepad.right_trigger_float(
            0.0
        )

        gamepad.left_trigger_float(
            0.0
        )

        # ====================================================
        # CLEAR DIGITAL ACCEL/BRAKE
        # ====================================================

        gamepad.release_button(
            vg.XUSB_BUTTON.XUSB_GAMEPAD_A
        )

        gamepad.release_button(
            vg.XUSB_BUTTON.XUSB_GAMEPAD_B
        )

        # ====================================================
        # BOTH FISTS = ACCELERATOR
        # ====================================================

        if (
            not left_open
            and
            not right_open
        ):

            # ----------------------------------------------
            # ANALOG RT
            # ----------------------------------------------

            gamepad.right_trigger_float(
                FULL_THROTTLE
            )

            # ----------------------------------------------
            # DIGITAL A BACKUP
            # ----------------------------------------------

            gamepad.press_button(
                vg.XUSB_BUTTON.XUSB_GAMEPAD_A
            )

            mode = "ACCEL"

        # ====================================================
        # BOTH OPEN = BRAKE
        # ====================================================

        elif (
            left_open
            and
            right_open
        ):

            # ----------------------------------------------
            # ANALOG LT
            # ----------------------------------------------

            gamepad.left_trigger_float(
                FULL_BRAKE
            )

            # ----------------------------------------------
            # DIGITAL B BACKUP
            # ----------------------------------------------

            gamepad.press_button(
                vg.XUSB_BUTTON.XUSB_GAMEPAD_B
            )

            mode = "BRAKE"

        # ====================================================
        # ONE FIST + ONE OPEN = COAST
        # ====================================================

        else:

            mode = "NEUTRAL"

        # ====================================================
        # SEND EVERYTHING
        # ====================================================

        gamepad.update()

        return mode


# ============================================================
# DRAW STEERING WHEEL
# ============================================================

def draw_steering_wheel(
    frame,
    center,
    angle_deg,
    direction,
    strength
):

    h, w = frame.shape[:2]

    radius = int(
        min(w, h)
        *
        0.10
    )

    cx, cy = center

    color = CLR_NEUTRAL

    if direction == "LEFT":

        color = CLR_LEFT

    elif direction == "RIGHT":

        color = CLR_RIGHT

    # Shadow
    cv2.circle(
        frame,
        (
            cx + 3,
            cy + 3
        ),
        radius,
        (0, 0, 0),
        4
    )

    # Wheel
    cv2.circle(
        frame,
        (
            cx,
            cy
        ),
        radius,
        color,
        3
    )

    # Wheel spokes
    for sa in [
        0,
        120,
        240
    ]:

        rad = math.radians(
            sa - angle_deg
        )

        x1 = int(
            cx
            +
            radius
            *
            0.4
            *
            math.cos(rad)
        )

        y1 = int(
            cy
            -
            radius
            *
            0.4
            *
            math.sin(rad)
        )

        x2 = int(
            cx
            +
            radius
            *
            0.95
            *
            math.cos(rad)
        )

        y2 = int(
            cy
            -
            radius
            *
            0.95
            *
            math.sin(rad)
        )

        cv2.line(
            frame,
            (
                x1,
                y1
            ),
            (
                x2,
                y2
            ),
            color,
            2
        )

    cv2.circle(
        frame,
        (
            cx,
            cy
        ),
        6,
        color,
        -1
    )


# ============================================================
# DRAW HUD
# ============================================================

def draw_hud(
    frame,
    angle,
    direction,
    strength,
    throttle_mode,
    both_hands_visible,
    left_open,
    right_open,
    fps
):

    h, w = frame.shape[:2]

    # --------------------------------------------------------
    # Bottom panel
    # --------------------------------------------------------

    overlay = frame.copy()

    cv2.rectangle(
        overlay,
        (
            0,
            h - 190
        ),
        (
            w,
            h
        ),
        (
            10,
            10,
            20
        ),
        -1
    )

    cv2.addWeighted(
        overlay,
        0.65,
        frame,
        0.35,
        0,
        frame
    )

    # --------------------------------------------------------
    # Steering bar
    # --------------------------------------------------------

    bar_w = int(
        w * 0.5
    )

    bar_h = 14

    bar_x = (
        w - bar_w
    ) // 2

    bar_y = h - 135

    cv2.rectangle(
        frame,
        (
            bar_x,
            bar_y
        ),
        (
            bar_x + bar_w,
            bar_y + bar_h
        ),
        (
            50,
            50,
            60
        ),
        -1
    )

    mid = (
        bar_x
        +
        bar_w // 2
    )

    cv2.rectangle(
        frame,
        (
            mid - 2,
            bar_y - 4
        ),
        (
            mid + 2,
            bar_y + bar_h + 4
        ),
        (
            180,
            180,
            180
        ),
        -1
    )

    fill_len = int(
        (
            bar_w // 2
        )
        *
        strength
    )

    if (
        direction == "LEFT"
        and
        fill_len > 0
    ):

        cv2.rectangle(
            frame,
            (
                mid - fill_len,
                bar_y
            ),
            (
                mid,
                bar_y + bar_h
            ),
            CLR_LEFT,
            -1
        )

    elif (
        direction == "RIGHT"
        and
        fill_len > 0
    ):

        cv2.rectangle(
            frame,
            (
                mid,
                bar_y
            ),
            (
                mid + fill_len,
                bar_y + bar_h
            ),
            CLR_RIGHT,
            -1
        )

    font = cv2.FONT_HERSHEY_SIMPLEX

    dir_color = (
        CLR_LEFT
        if direction == "LEFT"
        else
        CLR_RIGHT
        if direction == "RIGHT"
        else
        CLR_NEUTRAL
    )

    cv2.putText(
        frame,
        "<- LEFT",
        (
            bar_x,
            bar_y - 10
        ),
        font,
        0.45,
        CLR_LEFT,
        1
    )

    cv2.putText(
        frame,
        "RIGHT ->",
        (
            bar_x + bar_w - 80,
            bar_y - 10
        ),
        font,
        0.45,
        CLR_RIGHT,
        1
    )

    cv2.putText(
        frame,
        direction,
        (
            mid - 30,
            bar_y + bar_h + 28
        ),
        font,
        0.8,
        dir_color,
        2
    )

    # --------------------------------------------------------
    # Angle
    # --------------------------------------------------------

    if SHOW_ANGLE:

        cv2.putText(
            frame,
            f"{angle:+.1f} deg",
            (
                bar_x,
                h - 105
            ),
            font,
            0.55,
            CLR_TEXT,
            1
        )

    # --------------------------------------------------------
    # Steering strength
    # --------------------------------------------------------

    cv2.putText(
        frame,
        f"STEERING: {strength * 100:.0f}%",
        (
            bar_x + 150,
            h - 105
        ),
        font,
        0.55,
        CLR_TEXT,
        1
    )

    # --------------------------------------------------------
    # Accelerator / brake status
    # --------------------------------------------------------

    if throttle_mode == "ACCEL":

        throttle_color = CLR_ACCEL

        throttle_label = (
            "ACCELERATOR  RT + A  [100%]"
        )

    elif throttle_mode == "BRAKE":

        throttle_color = CLR_BRAKE

        throttle_label = (
            "BRAKE  LT + B  [100%]"
        )

    else:

        throttle_color = CLR_NEUTRAL

        throttle_label = "NEUTRAL / COAST"

    cv2.rectangle(
        frame,
        (
            bar_x,
            h - 78
        ),
        (
            bar_x + bar_w,
            h - 48
        ),
        (
            30,
            30,
            40
        ),
        -1
    )

    cv2.rectangle(
        frame,
        (
            bar_x,
            h - 78
        ),
        (
            bar_x + bar_w,
            h - 48
        ),
        throttle_color,
        2
    )

    cv2.putText(
        frame,
        throttle_label,
        (
            bar_x + 10,
            h - 57
        ),
        font,
        0.55,
        throttle_color,
        2
    )

    # --------------------------------------------------------
    # Hand states
    # --------------------------------------------------------

    l_label = (
        "OPEN"
        if left_open
        else
        "FIST"
    )

    r_label = (
        "OPEN"
        if right_open
        else
        "FIST"
    )

    cv2.putText(
        frame,
        f"L: {l_label}",
        (
            bar_x + bar_w + 10,
            h - 105
        ),
        font,
        0.5,
        CLR_TEXT,
        1
    )

    cv2.putText(
        frame,
        f"R: {r_label}",
        (
            bar_x + bar_w + 10,
            h - 80
        ),
        font,
        0.5,
        CLR_TEXT,
        1
    )

    # --------------------------------------------------------
    # FPS
    # --------------------------------------------------------

    cv2.putText(
        frame,
        f"FPS: {fps:.0f}",
        (
            w - 90,
            30
        ),
        font,
        0.55,
        CLR_ACCENT,
        1
    )

    # --------------------------------------------------------
    # Hand visibility
    # --------------------------------------------------------

    status = (
        "BOTH HANDS DETECTED"
        if both_hands_visible
        else
        "SHOW BOTH HANDS"
    )

    status_color = (
        (60, 220, 60)
        if both_hands_visible
        else
        (0, 80, 255)
    )

    cv2.putText(
        frame,
        status,
        (
            10,
            30
        ),
        font,
        0.55,
        status_color,
        1
    )

    # --------------------------------------------------------
    # Steering wheel
    # --------------------------------------------------------

    draw_steering_wheel(
        frame,
        (
            w - 80,
            h - 80
        ),
        angle,
        direction,
        strength
    )


# ============================================================
# DRAW HAND CONNECTION
# ============================================================

def draw_hand_connection(
    frame,
    lw,
    rw
):

    lx, ly = lw
    rx, ry = rw

    # Shadow
    cv2.line(
        frame,
        (
            lx,
            ly
        ),
        (
            rx,
            ry
        ),
        (
            30,
            100,
            200
        ),
        8
    )

    # Main line
    cv2.line(
        frame,
        (
            lx,
            ly
        ),
        (
            rx,
            ry
        ),
        CLR_ACCENT,
        2
    )

    # Left wrist
    cv2.circle(
        frame,
        (
            lx,
            ly
        ),
        10,
        CLR_HAND_L,
        -1
    )

    # Right wrist
    cv2.circle(
        frame,
        (
            rx,
            ry
        ),
        10,
        CLR_HAND_R,
        -1
    )

    # Center
    mx = (
        lx + rx
    ) // 2

    my = (
        ly + ry
    ) // 2

    cv2.circle(
        frame,
        (
            mx,
            my
        ),
        7,
        CLR_WHEEL,
        -1
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # --------------------------------------------------------
    # Camera backend
    # --------------------------------------------------------

    backend = (
        cv2.CAP_AVFOUNDATION
        if platform.system() == "Darwin"
        else cv2.CAP_ANY
    )

    cap = cv2.VideoCapture(
        CAMERA_INDEX,
        backend
    )

    if not cap.isOpened():

        cap = cv2.VideoCapture(
            CAMERA_INDEX
        )

    if not cap.isOpened():

        print(
            "[ERROR] Cannot open camera."
        )

        return

    cap.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        640
    )

    cap.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        480
    )

    cap.set(
        cv2.CAP_PROP_FPS,
        60
    )

    # --------------------------------------------------------
    # Controller
    # --------------------------------------------------------

    controller = SteeringController()

    # --------------------------------------------------------
    # MediaPipe
    # --------------------------------------------------------

    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        model_complexity=0,
        min_detection_confidence=MIN_DETECTION_CONF,
        min_tracking_confidence=MIN_TRACKING_CONF
    )

    # Drawing styles

    conn_style = mp_drawing.DrawingSpec(
        color=(80, 80, 100),
        thickness=1
    )

    landmark_style = mp_drawing.DrawingSpec(
        color=(200, 200, 255),
        thickness=1,
        circle_radius=2
    )

    # --------------------------------------------------------
    # State
    # --------------------------------------------------------

    prev_time = time.time()

    angle = 0.0

    direction = "STRAIGHT"

    strength = 0.0

    throttle_mode = "NEUTRAL"

    left_open = False

    right_open = False

    lost_frames = 0

    # --------------------------------------------------------
    # Startup
    # --------------------------------------------------------

    print()
    print("=" * 65)
    print(
        "       HAND GESTURE VIRTUAL XBOX CONTROLLER"
    )
    print("=" * 65)
    print()
    print("STEERING")
    print(
        "  Hand tilt LEFT  -> Analog LEFT"
    )
    print(
        "  Hand tilt RIGHT -> Analog RIGHT"
    )
    print()
    print("ACCELERATION")
    print(
        "  BOTH FISTS -> RT 100% + A"
    )
    print()
    print("BRAKE")
    print(
        "  BOTH OPEN HANDS -> LT 100% + B"
    )
    print()
    print("COAST")
    print(
        "  ONE FIST + ONE OPEN HAND"
    )
    print()
    print("SAFETY")
    print(
        "  Hands disappear -> all controls released"
    )
    print()
    print("Press Q or ESC to quit.")
    print("=" * 65)
    print()

    # --------------------------------------------------------
    # Main loop
    # --------------------------------------------------------

    try:

        while True:

            ret, frame = cap.read()

            if (
                not ret
                or
                frame is None
            ):

                time.sleep(
                    0.01
                )

                continue

            # ------------------------------------------------
            # Mirror
            # ------------------------------------------------

            if FLIP_CAMERA:

                frame = cv2.flip(
                    frame,
                    1
                )

            h, w = frame.shape[:2]

            # ------------------------------------------------
            # RGB
            # ------------------------------------------------

            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            rgb.flags.writeable = False

            results = hands.process(
                rgb
            )

            rgb.flags.writeable = True

            both_visible = False

            # =================================================
            # DETECT HANDS
            # =================================================

            if (
                results.multi_hand_landmarks
                and
                results.multi_handedness
            ):

                hand_data = {}

                for (
                    hand_landmarks,
                    handedness
                ) in zip(
                    results.multi_hand_landmarks,
                    results.multi_handedness
                ):

                    label = (
                        handedness
                        .classification[0]
                        .label
                    )

                    # Draw hand
                    mp_drawing.draw_landmarks(
                        frame,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        landmark_style,
                        conn_style
                    )

                    # Wrist
                    wrist = (
                        hand_landmarks
                        .landmark[0]
                    )

                    wx = int(
                        wrist.x * w
                    )

                    wy = int(
                        wrist.y * h
                    )

                    opened = is_open_hand(
                        hand_landmarks
                    )

                    hand_data[label] = (
                        wrist.x,
                        wrist.y,
                        wx,
                        wy,
                        opened
                    )

                # =================================================
                # BOTH HANDS
                # =================================================

                if (
                    "Left" in hand_data
                    and
                    "Right" in hand_data
                ):

                    both_visible = True

                    lost_frames = 0

                    (
                        lx_n,
                        ly_n,
                        lx_px,
                        ly_px,
                        left_open
                    ) = hand_data["Left"]

                    (
                        rx_n,
                        ry_n,
                        rx_px,
                        ry_px,
                        right_open
                    ) = hand_data["Right"]

                    # Draw hand-to-hand wheel line

                    draw_hand_connection(
                        frame,
                        (
                            lx_px,
                            ly_px
                        ),
                        (
                            rx_px,
                            ry_px
                        )
                    )

                    # =================================================
                    # STEERING
                    # =================================================

                    (
                        angle,
                        direction,
                        strength
                    ) = controller.update_steer(
                        (
                            lx_n,
                            ly_n
                        ),
                        (
                            rx_n,
                            ry_n
                        )
                    )

                    # =================================================
                    # ACCELERATOR / BRAKE
                    # =================================================

                    throttle_mode = (
                        controller.update_throttle(
                            left_open,
                            right_open
                        )
                    )

                else:

                    lost_frames += 1

            else:

                lost_frames += 1

            # =================================================
            # SAFETY
            # =================================================

            if (
                lost_frames
                >=
                GRACE_FRAMES
            ):

                controller.release_all()

                angle = 0.0

                direction = "STRAIGHT"

                strength = 0.0

                throttle_mode = "NEUTRAL"

                left_open = False

                right_open = False

            # =================================================
            # FPS
            # =================================================

            now = time.time()

            fps = (
                1.0
                /
                max(
                    now - prev_time,
                    1e-6
                )
            )

            prev_time = now

            # =================================================
            # HUD
            # =================================================

            draw_hud(
                frame,
                angle,
                direction,
                strength,
                throttle_mode,
                both_visible,
                left_open,
                right_open,
                fps
            )

            # =================================================
            # DISPLAY
            # =================================================

            cv2.imshow(
                "Virtual Steering Wheel",
                frame
            )

            # =================================================
            # EXIT
            # =================================================

            key = (
                cv2.waitKey(1)
                &
                0xFF
            )

            if key in (
                ord("q"),
                ord("Q"),
                27
            ):

                break

    finally:

        # =====================================================
        # SAFETY RELEASE
        # =====================================================

        controller.release_all()

        hands.close()

        cap.release()

        cv2.destroyAllWindows()

        print()
        print(
            "[OK] All controller inputs released."
        )

        print(
            "[OK] Camera closed."
        )

        print(
            "[OK] Program stopped."
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()