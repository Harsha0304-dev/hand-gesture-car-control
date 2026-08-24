import cv2
import mediapipe as mp
import vgamepad as vg
import math
import time
import webbrowser


# ============================================================
# DRIVER CLUB HIGHWAY RACING
# HAND GESTURE XBOX CONTROLLER
# ============================================================

GAME_URL = (
    "https://www.crazygames.com/game/"
    "driver-club-highway-racing"
)


# ============================================================
# CAMERA SETTINGS
# ============================================================

CAMERA_INDEX = 0

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480


# ============================================================
# YOUR STEERING SENSITIVITY
# ============================================================

# Small movements are ignored.
DEAD_ZONE_DEG = 5.0

# Maximum steering angle.
MAX_STEER_DEG = 32.0

# Steering response curve.
STEER_CURVE = 0.68

# Hand-angle smoothing.
ANGLE_SMOOTHING = 0.18

# Final steering smoothing.
STEERING_SMOOTHING = 0.28


# ============================================================
# HAND DETECTION
# ============================================================

OPEN_FINGER_THRESHOLD = 3

MIN_DETECTION_CONF = 0.65
MIN_TRACKING_CONF = 0.55

HAND_TIMEOUT = 0.40


# ============================================================
# THROTTLE SETTINGS
# ============================================================

# 255 = full trigger
FULL_TRIGGER = 255

# If True:
#
# BOTH FISTS  -> RT
# BOTH OPEN   -> LT
#
# This is the safest configuration for a racing game.
USE_ANALOG_TRIGGERS = True


# ============================================================
# MEDIAPIPE
# ============================================================

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils


hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    model_complexity=0,
    min_detection_confidence=MIN_DETECTION_CONF,
    min_tracking_confidence=MIN_TRACKING_CONF
)


# ============================================================
# VIRTUAL XBOX CONTROLLER
# ============================================================

print()
print("[INFO] Creating virtual Xbox controller...")

gamepad = vg.VX360Gamepad()

print("[OK] Virtual Xbox controller created.")


# ============================================================
# CAMERA
# ============================================================

print("[INFO] Starting camera...")

cap = cv2.VideoCapture(
    CAMERA_INDEX,
    cv2.CAP_DSHOW
)

if not cap.isOpened():

    print(
        "[WARNING] DirectShow camera open failed."
    )

    cap = cv2.VideoCapture(
        CAMERA_INDEX
    )


if not cap.isOpened():

    print()
    print("[ERROR] Cannot open camera.")
    print()
    print("Check:")
    print("  Windows Camera permissions")
    print("  Camera not being used by another program")
    print()

    raise SystemExit


cap.set(
    cv2.CAP_PROP_FRAME_WIDTH,
    CAMERA_WIDTH
)

cap.set(
    cv2.CAP_PROP_FRAME_HEIGHT,
    CAMERA_HEIGHT
)


print("[OK] Camera opened.")


# ============================================================
# STATE
# ============================================================

current_angle = 0.0

current_steering = 0.0

last_hand_time = time.time()

left_open = False
right_open = False

current_mode = "WAITING"

current_throttle = 0

current_brake = 0


# ============================================================
# UTILITY
# ============================================================

def clamp(
    value,
    minimum,
    maximum
):

    return max(
        minimum,
        min(
            maximum,
            value
        )
    )


# ============================================================
# OPEN-HAND DETECTION
# ============================================================

def is_open_hand(hand):

    """
    Detect whether a hand is open.

    We examine the four fingers:
        index
        middle
        ring
        pinky

    Thumb is intentionally ignored because
    camera orientation can make thumb detection
    unreliable.
    """

    finger_tips = [
        8,   # index
        12,  # middle
        16,  # ring
        20   # pinky
    ]

    finger_pips = [
        6,
        10,
        14,
        18
    ]

    extended = 0

    for tip, pip in zip(
        finger_tips,
        finger_pips
    ):

        if (
            hand.landmark[tip].y
            <
            hand.landmark[pip].y
        ):

            extended += 1


    return (
        extended
        >=
        OPEN_FINGER_THRESHOLD
    )


# ============================================================
# STEERING CALCULATION
# ============================================================

def calculate_steering(
    left_wrist,
    right_wrist
):

    global current_angle
    global current_steering


    # --------------------------------------------------------
    # Calculate angle between the two wrists.
    # --------------------------------------------------------

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


    raw_angle = math.degrees(
        math.atan2(
            dy,
            dx
        )
    )


    # --------------------------------------------------------
    # Smooth raw angle.
    # --------------------------------------------------------

    current_angle += (
        raw_angle
        -
        current_angle
    ) * ANGLE_SMOOTHING


    # --------------------------------------------------------
    # DEAD ZONE
    # --------------------------------------------------------

    if (
        abs(current_angle)
        <=
        DEAD_ZONE_DEG
    ):

        target = 0.0


    else:

        magnitude = (
            abs(current_angle)
            -
            DEAD_ZONE_DEG
        ) / (
            MAX_STEER_DEG
            -
            DEAD_ZONE_DEG
        )


        magnitude = clamp(
            magnitude,
            0.0,
            1.0
        )


        # Sensitivity curve.
        magnitude = (
            magnitude
            **
            STEER_CURVE
        )


        if current_angle > 0:

            target = magnitude

        else:

            target = -magnitude


    # --------------------------------------------------------
    # Smooth final steering.
    # --------------------------------------------------------

    current_steering += (
        target
        -
        current_steering
    ) * STEERING_SMOOTHING


    return clamp(
        current_steering,
        -1.0,
        1.0
    )


# ============================================================
# RELEASE ALL CONTROLLER INPUTS
# ============================================================

def release_controller():

    global current_throttle
    global current_brake


    # Steering center.
    gamepad.left_joystick_float(
        0.0,
        0.0
    )


    # Release triggers.
    gamepad.right_trigger(
        0
    )

    gamepad.left_trigger(
        0
    )


    # Release common buttons as a safety measure.
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


    current_throttle = 0
    current_brake = 0


# ============================================================
# SEND HAND CONTROLS TO XBOX CONTROLLER
# ============================================================

def send_controller(
    steering,
    left_is_open,
    right_is_open
):

    global current_mode
    global current_throttle
    global current_brake


    # ========================================================
    # STEERING
    # ========================================================

    gamepad.left_joystick_float(
        steering,
        0.0
    )


    # ========================================================
    # DETERMINE GESTURE
    # ========================================================

    both_fists = (
        not left_is_open
        and
        not right_is_open
    )


    both_open = (
        left_is_open
        and
        right_is_open
    )


    mixed_hands = (
        left_is_open
        !=
        right_is_open
    )


    # ========================================================
    # ALWAYS CLEAR OLD TRIGGER VALUES FIRST
    # ========================================================

    gamepad.right_trigger(
        0
    )

    gamepad.left_trigger(
        0
    )


    # ========================================================
    # BOTH FISTS = ACCELERATE
    # ========================================================

    if both_fists:

        gamepad.right_trigger(
            FULL_TRIGGER
        )

        current_throttle = 255
        current_brake = 0

        current_mode = (
            "ACCELERATE"
        )


    # ========================================================
    # BOTH OPEN = BRAKE
    # ========================================================

    elif both_open:

        gamepad.left_trigger(
            FULL_TRIGGER
        )

        current_throttle = 0
        current_brake = 255

        current_mode = (
            "BRAKE"
        )


    # ========================================================
    # ONE OPEN + ONE FIST = COAST
    # ========================================================

    elif mixed_hands:

        current_throttle = 0
        current_brake = 0

        current_mode = (
            "COAST"
        )


    # ========================================================
    # SEND
    # ========================================================

    gamepad.update()

    return current_mode


# ============================================================
# DRAW TEXT
# ============================================================

def draw_text(
    frame,
    text,
    position,
    scale=0.7,
    color=(255, 255, 255),
    thickness=2
):

    cv2.putText(
        frame,
        text,
        position,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA
    )


# ============================================================
# STARTUP
# ============================================================

print()
print("=" * 65)
print("        HAND GESTURE RACING CONTROLLER")
print("=" * 65)
print()
print("GAME:")
print("Driver Club Highway Racing")
print()
print("GESTURES:")
print()
print("  Tilt hands LEFT       -> STEER LEFT")
print("  Hands CENTER          -> STRAIGHT")
print("  Tilt hands RIGHT      -> STEER RIGHT")
print()
print("  BOTH FISTS            -> ACCELERATE")
print("  BOTH OPEN HANDS       -> BRAKE")
print("  ONE FIST + ONE OPEN   -> COAST")
print()
print("SENSITIVITY:")
print()
print(f"  Dead zone     : {DEAD_ZONE_DEG} degrees")
print(f"  Max steering  : {MAX_STEER_DEG} degrees")
print(f"  Curve         : {STEER_CURVE}")
print()
print("Press Q or ESC in the camera window to quit.")
print()
print("=" * 65)
print()


# ============================================================
# OPEN CRAZYGAMES
# ============================================================

print(
    "[INFO] Opening Driver Club Highway Racing..."
)

webbrowser.open(
    GAME_URL
)


print(
    "[INFO] Click inside the game once after it opens."
)

print(
    "[INFO] Waiting for browser..."
)

time.sleep(4)


# ============================================================
# MAIN LOOP
# ============================================================

try:

    while True:

        # ----------------------------------------------------
        # CAMERA FRAME
        # ----------------------------------------------------

        ret, frame = cap.read()


        if not ret:

            print(
                "[ERROR] Could not read camera frame."
            )

            break


        # Mirror image.
        frame = cv2.flip(
            frame,
            1
        )


        # ----------------------------------------------------
        # MEDIAPIPE
        # ----------------------------------------------------

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )


        results = hands.process(
            rgb
        )


        detected = {}


        # ----------------------------------------------------
        # PROCESS DETECTED HANDS
        # ----------------------------------------------------

        if (
            results.multi_hand_landmarks
            is not None
        ):

            for index, hand in enumerate(
                results.multi_hand_landmarks
            ):

                # Draw skeleton.
                mp_draw.draw_landmarks(
                    frame,
                    hand,
                    mp_hands.HAND_CONNECTIONS
                )


                # --------------------------------------------
                # Handedness
                # --------------------------------------------

                if (
                    results.multi_handedness
                    and
                    index
                    <
                    len(
                        results.multi_handedness
                    )
                ):

                    label = (
                        results
                        .multi_handedness[index]
                        .classification[0]
                        .label
                    )

                else:

                    label = str(index)


                wrist = (
                    hand.landmark[0]
                )


                detected[label] = (
                    wrist.x,
                    wrist.y,
                    is_open_hand(hand)
                )


        # ====================================================
        # TWO HANDS DETECTED
        # ====================================================

        if (
            "Left" in detected
            and
            "Right" in detected
        ):

            (
                lx,
                ly,
                left_open
            ) = detected["Left"]


            (
                rx,
                ry,
                right_open
            ) = detected["Right"]


            # ----------------------------------------------
            # Steering
            # ----------------------------------------------

            steering = calculate_steering(
                (
                    lx,
                    ly
                ),
                (
                    rx,
                    ry
                )
            )


            # ----------------------------------------------
            # Throttle / brake
            # ----------------------------------------------

            mode = send_controller(
                steering,
                left_open,
                right_open
            )


            last_hand_time = (
                time.time()
            )


        # ====================================================
        # LESS THAN TWO HANDS
        # ====================================================

        else:

            if (
                time.time()
                -
                last_hand_time
                >
                HAND_TIMEOUT
            ):

                release_controller()


                current_mode = (
                    "NO HANDS - SAFE"
                )


                current_steering = (
                    current_steering
                    *
                    0.85
                )


                steering = (
                    current_steering
                )


            else:

                steering = (
                    current_steering
                )


        # ====================================================
        # CAMERA HUD
        # ====================================================

        # ----------------------------------------------------
        # Title
        # ----------------------------------------------------

        draw_text(
            frame,
            "HAND CONTROLLER",
            (
                20,
                32
            ),
            0.8,
            (
                0,
                255,
                255
            ),
            2
        )


        # ----------------------------------------------------
        # ANGLE
        # ----------------------------------------------------

        draw_text(
            frame,
            f"Hand angle: {current_angle:+.1f} deg",
            (
                20,
                68
            ),
            0.65,
            (
                255,
                255,
                255
            ),
            2
        )


        # ----------------------------------------------------
        # STEERING
        # ----------------------------------------------------

        draw_text(
            frame,
            f"Steering: {current_steering:+.2f}",
            (
                20,
                100
            ),
            0.65,
            (
                0,
                255,
                0
            ),
            2
        )


        # ----------------------------------------------------
        # MODE
        # ----------------------------------------------------

        mode_color = (
            0,
            255,
            0
        )


        if current_mode == "BRAKE":

            mode_color = (
                0,
                100,
                255
            )


        elif (
            "NO HANDS"
            in
            current_mode
        ):

            mode_color = (
                0,
                0,
                255
            )


        draw_text(
            frame,
            f"MODE: {current_mode}",
            (
                20,
                135
            ),
            0.7,
            mode_color,
            2
        )


        # ----------------------------------------------------
        # TRIGGER VALUES
        # ----------------------------------------------------

        draw_text(
            frame,
            f"RT THROTTLE: {current_throttle}",
            (
                20,
                170
            ),
            0.6,
            (
                0,
                255,
                255
            ),
            2
        )


        draw_text(
            frame,
            f"LT BRAKE: {current_brake}",
            (
                20,
                202
            ),
            0.6,
            (
                0,
                180,
                255
            ),
            2
        )


        # ====================================================
        # STEERING BAR
        # ====================================================

        bar_left = 120
        bar_right = 520
        bar_y = 250


        # Main line
        cv2.line(
            frame,
            (
                bar_left,
                bar_y
            ),
            (
                bar_right,
                bar_y
            ),
            (
                150,
                150,
                150
            ),
            5
        )


        # Center marker
        center_x = (
            bar_left
            +
            bar_right
        ) // 2


        cv2.line(
            frame,
            (
                center_x,
                bar_y - 15
            ),
            (
                center_x,
                bar_y + 15
            ),
            (
                255,
                255,
                255
            ),
            2
        )


        # Steering position
        marker_x = int(
            center_x
            +
            current_steering
            *
            (
                (
                    bar_right
                    -
                    bar_left
                )
                //
                2
            )
        )


        cv2.circle(
            frame,
            (
                marker_x,
                bar_y
            ),
            12,
            (
                0,
                255,
                0
            ),
            -1
        )


        draw_text(
            frame,
            "LEFT",
            (
                55,
                255
            ),
            0.55,
            (
                255,
                255,
                255
            ),
            2
        )


        draw_text(
            frame,
            "RIGHT",
            (
                525,
                255
            ),
            0.55,
            (
                255,
                255,
                255
            ),
            2
        )


        # ====================================================
        # GESTURE INSTRUCTIONS
        # ====================================================

        draw_text(
            frame,
            "BOTH FISTS = ACCELERATE",
            (
                20,
                300
            ),
            0.55,
            (
                255,
                255,
                255
            ),
            2
        )


        draw_text(
            frame,
            "BOTH OPEN = BRAKE",
            (
                20,
                330
            ),
            0.55,
            (
                255,
                255,
                255
            ),
            2
        )


        draw_text(
            frame,
            "Q / ESC = EXIT",
            (
                20,
                360
            ),
            0.55,
            (
                200,
                200,
                200
            ),
            2
        )


        # ====================================================
        # SHOW CAMERA
        # ====================================================

        cv2.imshow(
            "Hand Controller - Driver Club Highway Racing",
            frame
        )


        # ----------------------------------------------------
        # KEYBOARD ONLY FOR EXIT
        # ----------------------------------------------------

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


# ============================================================
# CLEANUP
# ============================================================

finally:

    print()
    print(
        "[INFO] Releasing controller..."
    )


    release_controller()


    print(
        "[INFO] Releasing camera..."
    )


    cap.release()


    print(
        "[INFO] Closing MediaPipe..."
    )


    hands.close()


    cv2.destroyAllWindows()


    print()
    print(
        "[OK] Controller released."
    )

    print(
        "[OK] Program closed."
    )
