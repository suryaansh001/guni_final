import multiprocessing
import time
import random
import os
import asyncio
import platform
import pygame
from PIL import Image

# Emotion frame counts from the original code
frame_count = {
    'blink': 39,
    'happy': 60,
    'sad': 47,
    'dizzy': 67,
    'excited': 24,
    'neutral': 61,
    'happy2': 20,
    'angry': 20,
    'happy3': 26,
    'bootup3': 124,
    'blink2': 20
}

# Emotion lists
emotion = ['angry', 'sad', 'excited']
normal = ['neutral', 'blink2']

# Multiprocessing queue and event for emotion handling
q = multiprocessing.Queue()
event = multiprocessing.Event()

# Pygame setup
pygame.init()
screen = pygame.display.set_mode((800, 800))  # Adjust to match your PNG resolution
pygame.display.set_caption("Emotion Simulator")
FPS = 60
clock = pygame.time.Clock()

# Simulated sensor check
# ...existing code...

# Simulated sensor check: show all emotions one by one in order
def check_sensor():
    emotion_sequence = emotion + normal
    idx = 0
    while True:
        time.sleep(1)  # Simulate sensor check delay
        emotion_triggered = emotion_sequence[idx % len(emotion_sequence)]
        print(f"Sensor triggered emotion: {emotion_triggered.upper()}")
        q.put(emotion_triggered)
        event.set()  # Notify the main process of the new emotion
        idx += 1

# ...existing code...
# Simulated servo movements
def happy():
    print("Displaying HAPPY emotion: Waving arms and tilting base")
    for i in range(5):
        print(f"Happy cycle {i+1}: Moving servos up and down")
        time.sleep(0.5)

def angry():
    print("Displaying ANGRY emotion: Shaking base")
    for i in range(5):
        print(f"Angry cycle {i+1}: Base rotates randomly")
        time.sleep(0.5)

def sad():
    print("Displaying SAD emotion: Lowering arms and tilting base")
    for i in range(60):
        print(f"Sad frame {i+1}: Base tilts slightly")
        time.sleep(0.09)

def excited():
    print("Displaying EXCITED emotion: Rapid base tilting")
    for i in range(120):
        print(f"Excited frame {i+1}: Base tilts dynamically")
        time.sleep(0.01)

def blink():
    print("Displaying BLINK emotion: Eyes blinking")
    time.sleep(1)

# Display function using Pygame in the main process
async def show(emotion, count, screen):
    emotion_dir = f"/home/sury/proj/guni/emotion_png_showing/Emo/Code/emotions/{emotion}"
    if not os.path.exists(emotion_dir):
        print(f"No directory found for {emotion}")
        return
    for i in range(count):
        print(f"Showing {emotion.upper()} (loop {i+1}/{count})")
        for frame in range(frame_count.get(emotion, 1)):
            frame_path = f"{emotion_dir}/frame{frame}.png"
            if os.path.exists(frame_path):
                try:
                    pil_image = Image.open(frame_path)
                    mode = pil_image.mode
                    size = pil_image.size
                    data = pil_image.tobytes()
                    pygame_image = pygame.image.fromstring(data, size, mode)
                    screen.fill((0, 0, 0))  # Black background
                    screen.blit(pygame_image, (0, 0))
                    pygame.display.flip()
                    print(f"  Displaying frame {frame+1}/{frame_count.get(emotion, 1)} of {emotion}")
                    await asyncio.sleep(0.05)  # Frame display time
                except Exception as e:
                    print(f"  Error displaying frame {frame+1} of {emotion}: {e}")
            else:
                print(f"  Frame {frame+1} not found for {emotion}")
            # Check for quit event
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
            clock.tick(FPS)
        await asyncio.sleep(0.5)  # Pause between loops
    return True

# Simulated sound function
def sound(emotion):
    print(f"Playing sound for {emotion.upper()}")
    time.sleep(1)

# Bootup sequence
async def bootup(screen):
    print("Starting BOOTUP sequence")
    await show('bootup3', 1, screen)
    p2 = multiprocessing.Process(target=blink2_simulation)
    p3 = multiprocessing.Process(target=print, args=("Simulating servo rotation",))
    p4 = multiprocessing.Process(target=print, args=("Simulating base rotation",))
    p2.start()
    p3.start()
    p4.start()
    p4.join()
    p2.join()
    p3.join()

# Simulate blink2 for bootup
def blink2_simulation():
    print("Simulating BLINK2 (loop 1/3)")
    for frame in range(frame_count.get('blink2', 1)):
        print(f"  Simulating frame {frame+1}/{frame_count.get('blink2', 1)} of blink2")
        time.sleep(0.05)

async def main():
    # Start sensor simulation process
    p1 = multiprocessing.Process(target=check_sensor, name='p1')
    p1.start()
    
    # Run bootup sequence
    await bootup(screen)

    # Main loop
    running = True
    while running:
        for evt in pygame.event.get():
            if evt.type == pygame.QUIT:
                running = False
                break
        if event.is_set():
            for proc in multiprocessing.active_children():
                if proc.name == 'p5':
                    proc.terminate()
            event.clear()
            current_emotion = q.get()
            print(f"\n=== New Emotion Triggered: {current_emotion.upper()} ===\n")
            
            p3 = multiprocessing.Process(target=sound, args=(current_emotion,))
            if current_emotion == 'happy':
                p4 = multiprocessing.Process(target=happy)
            elif current_emotion == 'angry':
                p4 = multiprocessing.Process(target=angry)
            elif current_emotion == 'sad':
                p4 = multiprocessing.Process(target=sad)
            elif current_emotion == 'excited':
                p4 = multiprocessing.Process(target=excited)
            elif current_emotion == 'blink':
                p4 = multiprocessing.Process(target=blink)
            else:
                continue
            p3.start()
            p4.start()
            running = await show(current_emotion, 4, screen)
            p3.join()
            p4.join()
        else:
            for proc in multiprocessing.active_children():
                if proc.name not in ['p1', 'p5']:
                    proc.terminate()
            neutral = normal[0]
            print(f"\n=== Displaying Default: {neutral.upper()} ===\n")
            p5 = multiprocessing.Process(target=print, args=("Simulating base rotation for neutral",), name='p5')
            p5.start()
            running = await show(neutral, 4, screen)
            p5.join()
        clock.tick(FPS)
    
    # Cleanup
    p1.terminate()
    pygame.quit()

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == '__main__':
        asyncio.run(main())