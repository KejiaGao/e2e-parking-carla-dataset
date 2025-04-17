import carla

try:
    import pygame
    from pygame.locals import KMOD_CTRL
    from pygame.locals import KMOD_SHIFT
    from pygame.locals import K_0
    from pygame.locals import K_9
    from pygame.locals import K_BACKQUOTE
    from pygame.locals import K_BACKSPACE
    from pygame.locals import K_COMMA
    from pygame.locals import K_DOWN
    from pygame.locals import K_ESCAPE
    from pygame.locals import K_F1
    from pygame.locals import K_LEFT
    from pygame.locals import K_PERIOD
    from pygame.locals import K_RIGHT
    from pygame.locals import K_SLASH
    from pygame.locals import K_SPACE
    from pygame.locals import K_TAB
    from pygame.locals import K_UP
    from pygame.locals import K_a
    from pygame.locals import K_c
    from pygame.locals import K_d
    from pygame.locals import K_h
    from pygame.locals import K_m
    from pygame.locals import K_n
    from pygame.locals import K_p
    from pygame.locals import K_q
    from pygame.locals import K_r
    from pygame.locals import K_s
    from pygame.locals import K_w
    from pygame.locals import K_l
    from pygame.locals import K_i
    from pygame.locals import K_z
    from pygame.locals import K_x
    from pygame.locals import K_MINUS
    from pygame.locals import K_EQUALS
except ImportError:
    raise RuntimeError('cannot import pygame, make sure pygame package is installed')


class MultiControl(object):
    """Class that handles input of three devices: keyboard, gaming controller and wheel & pedals."""

    def __init__(self, world):
        self._world = world
        if isinstance(self._world.player, carla.Vehicle):
            self._control = carla.VehicleControl()
            self._lights = carla.VehicleLightState.NONE
            self._world.player.set_light_state(self._lights)
        else:
            raise NotImplementedError("Actor type not supported")
        self._steer_cache = 0.0
        self._world.hud.notification("Press 'H' or '?' for help.", seconds=4.0)
        # Initialize pygame joystick (for Xbox controller)
        pygame.init()
        if pygame.joystick.get_count() == 0:
            # raise RuntimeError('No joystick detected.')
            world.hud.notification("No joystick detected.")
        else:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            if self.joystick.get_numbuttons() < 18:
                self.input_device = 0 # Gaming controller. I use XBOX controller 2020.
            else:
                self.input_device = 1 # Wheel and pedals. I use Logitech G29 Driving Force Steering Wheels & Pedals.

    def parse_events(self, client, world, clock):
        # collision or restart task
        if self._world.need_init_ego_state:
            self._control = carla.VehicleControl()
            self._world.need_init_ego_state = False

        if isinstance(self._control, carla.VehicleControl):
            current_lights = self._lights
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            elif event.type == pygame.KEYUP:
                if self._is_quit_shortcut(event.key):
                    return True
                elif event.key == K_BACKSPACE:
                    world.keyboard_restart_task = True
                elif event.key == K_F1:
                    world.hud.toggle_info()
                elif event.key == K_h or (event.key == K_SLASH and pygame.key.get_mods() & KMOD_SHIFT):
                    world.hud.help.toggle()
                elif event.key == K_TAB:
                    world.camera_manager.toggle_camera()
                elif event.key == K_c and pygame.key.get_mods() & KMOD_SHIFT:
                    world.next_weather(reverse=True)
                elif event.key == K_c:
                    world.next_weather()
                elif event.key == K_BACKQUOTE:
                    world.camera_manager.next_sensor()
                elif event.key == K_n:
                    world.camera_manager.next_sensor()
                elif event.key > K_0 and event.key <= K_9:
                    world.camera_manager.set_sensor(event.key - 1 - K_0)
                elif event.key == K_r and (pygame.key.get_mods() & KMOD_CTRL):
                    if (world.recording_enabled):
                        client.stop_recorder()
                        world.recording_enabled = False
                        world.hud.notification("Recorder is OFF")
                    else:
                        client.start_recorder("manual_recording.rec")
                        world.recording_enabled = True
                        world.hud.notification("Recorder is ON")
                elif event.key == K_p and (pygame.key.get_mods() & KMOD_CTRL):
                    # stop recorder
                    client.stop_recorder()
                    world.recording_enabled = False
                    # work around to fix camera at start of replaying
                    current_index = world.camera_manager.index
                    world.destroy_sensors()
                    # disable autopilot
                    world.hud.notification("Replaying file 'manual_recording.rec'")
                    # replayer
                    client.replay_file("manual_recording.rec", world.recording_start, 0, 0)
                    world.camera_manager.set_sensor(current_index)
                elif event.key == K_MINUS and (pygame.key.get_mods() & KMOD_CTRL):
                    if pygame.key.get_mods() & KMOD_SHIFT:
                        world.recording_start -= 10
                    else:
                        world.recording_start -= 1
                    world.hud.notification("Recording start time is %d" % (world.recording_start))
                elif event.key == K_EQUALS and (pygame.key.get_mods() & KMOD_CTRL):
                    if pygame.key.get_mods() & KMOD_SHIFT:
                        world.recording_start += 10
                    else:
                        world.recording_start += 1
                    world.hud.notification("Recording start time is %d" % (world.recording_start))
                if isinstance(self._control, carla.VehicleControl):
                    if event.key == K_q:
                        self._control.gear = 1 if self._control.reverse else -1
                    elif event.key == K_m:
                        self._control.manual_gear_shift = not self._control.manual_gear_shift
                        self._control.gear = world.player.get_control().gear
                        world.hud.notification('%s Transmission' %
                                               ('Manual' if self._control.manual_gear_shift else 'Automatic'))
                    elif self._control.manual_gear_shift and event.key == K_COMMA:
                        self._control.gear = max(-1, self._control.gear - 1)
                    elif self._control.manual_gear_shift and event.key == K_PERIOD:
                        self._control.gear = self._control.gear + 1
                    elif event.key == K_l and pygame.key.get_mods() & KMOD_CTRL:
                        current_lights ^= carla.VehicleLightState.Special1
                    elif event.key == K_l and pygame.key.get_mods() & KMOD_SHIFT:
                        current_lights ^= carla.VehicleLightState.HighBeam
                    elif event.key == K_l:
                        # Use 'L' key to switch between lights:
                        # closed -> position -> low beam -> fog
                        if not self._lights & carla.VehicleLightState.Position:
                            world.hud.notification("Position lights")
                            current_lights |= carla.VehicleLightState.Position
                        else:
                            world.hud.notification("Low beam lights")
                            current_lights |= carla.VehicleLightState.LowBeam
                        if self._lights & carla.VehicleLightState.LowBeam:
                            world.hud.notification("Fog lights")
                            current_lights |= carla.VehicleLightState.Fog
                        if self._lights & carla.VehicleLightState.Fog:
                            world.hud.notification("Lights off")
                            current_lights ^= carla.VehicleLightState.Position
                            current_lights ^= carla.VehicleLightState.LowBeam
                            current_lights ^= carla.VehicleLightState.Fog
                    elif event.key == K_i:
                        current_lights ^= carla.VehicleLightState.Interior
                    elif event.key == K_z:
                        current_lights ^= carla.VehicleLightState.LeftBlinker
                    elif event.key == K_x:
                        current_lights ^= carla.VehicleLightState.RightBlinker
            elif event.type == pygame.JOYBUTTONDOWN and self.input_device == 0:
                if self.joystick.get_button(3): # Restart: Button 3 (Button Y)
                    world.keyboard_restart_task = True
                elif self.joystick.get_button(5): # Toggle view: Button 5 (RB, Right Bumper)
                    world.camera_manager.toggle_camera()                
                if isinstance(self._control, carla.VehicleControl):
                    if self.joystick.get_button(0): # Switch first / reverse gear: Button 0 (Button A)
                        self._control.gear = 1 if self._control.reverse else -1  
                    elif self.joystick.get_button(10): # Switch manual / automatic gear shift: Button 10 (RSB, Right Stick Button)
                        self._control.manual_gear_shift = not self._control.manual_gear_shift
                        self._control.gear = world.player.get_control().gear
                        world.hud.notification('%s Transmission' %
                                               ('Manual' if self._control.manual_gear_shift else 'Automatic'))                                                  
                    elif self._control.manual_gear_shift and self.joystick.get_button(2): # Manual downshift: Button 2 (Button X)
                        self._control.gear = max(-1, self._control.gear - 1)
                    elif self._control.manual_gear_shift and self.joystick.get_button(1): # Manual upshift: Button 1 (Button B)
                        self._control.gear = self._control.gear + 1
            elif event.type == pygame.JOYBUTTONDOWN and self.input_device == 1:
                if self.joystick.get_button(3): # Restart: Button 3 (Button Triangle)
                    world.keyboard_restart_task = True
                elif self.joystick.get_button(6): # Toggle view: Button 6 (R2)
                    world.camera_manager.toggle_camera()                
                if isinstance(self._control, carla.VehicleControl):
                    if self.joystick.get_button(4): # Switch first / reverse gear: Button 4 (Right paddle)
                        self._control.gear = 1 if self._control.reverse else -1  
                    elif self.joystick.get_button(10): # Switch manual / automatic gear shift: Button 10 (R3)
                        self._control.manual_gear_shift = not self._control.manual_gear_shift
                        self._control.gear = world.player.get_control().gear
                        world.hud.notification('%s Transmission' %
                                               ('Manual' if self._control.manual_gear_shift else 'Automatic'))                                                  
                    elif self._control.manual_gear_shift and self.joystick.get_button(5): # Manual downshift: Button 5 (Left paddle)
                        self._control.gear = max(-1, self._control.gear - 1)
                    elif self._control.manual_gear_shift and self.joystick.get_button(4): # Manual upshift: Button 4 (Right paddle)
                        self._control.gear = self._control.gear + 1
                

        if isinstance(self._control, carla.VehicleControl):
            self._parse_vehicle_keys(pygame.key.get_pressed(), clock.get_time())
            self._control.reverse = self._control.gear < 0
            # Set automatic control-related vehicle lights
            if self._control.brake:
                current_lights |= carla.VehicleLightState.Brake
            else:  # Remove the Brake flag
                current_lights &= ~carla.VehicleLightState.Brake
            if self._control.reverse:
                current_lights |= carla.VehicleLightState.Reverse
            else:  # Remove the Reverse flag
                current_lights &= ~carla.VehicleLightState.Reverse
            if current_lights != self._lights:  # Change the light state only if necessary
                self._lights = current_lights
                world.player.set_light_state(carla.VehicleLightState(self._lights))
        world.player.apply_control(self._control)

    def _parse_vehicle_keys(self, keys, milliseconds):
        if keys[K_UP] or keys[K_w]:
            self._control.throttle = min(self._control.throttle + 0.05, 0.5)
        else:
            self._control.throttle = 0.0

        if keys[K_DOWN] or keys[K_SPACE]:
            self._control.brake = min(self._control.brake + 0.2, 1)
        else:
            self._control.brake = 0

        steer_increment = 5e-4 * milliseconds
        if keys[K_LEFT] or keys[K_a]:
            if self._steer_cache > 0:
                self._steer_cache = 0
            else:
                self._steer_cache -= steer_increment
        elif keys[K_RIGHT] or keys[K_d]:
            if self._steer_cache < 0:
                self._steer_cache = 0
            else:
                self._steer_cache += steer_increment
        else:
            self._steer_cache = 0.0
        self._steer_cache = min(0.7, max(-0.7, self._steer_cache))
        self._control.steer = round(self._steer_cache, 1)
        self._control.hand_brake = keys[K_s]

        if pygame.joystick.get_count() != 0:            
            if self.input_device == 0:
                throttle = self.joystick.get_axis(5)  # Throttle: Axis 5 (RT, Right Trigger)
                brake = self.joystick.get_axis(2)     # Brake: Axis 2 (LT, Left Trigger)
                steer = self.joystick.get_axis(0)     # Steering: Axis 0 (LS, Left Stick)
                hand_brake = self.joystick.get_button(4)  # Handbrake: Button 4 (LB, Left Bumper)

                throttle = max(0, min(0.25 * (throttle + 1), 0.5)) # Ensure throttle value is within [0, 0.5]
                brake = max(0, min(0.5 * (brake + 1), 1)) # Ensure brake value is within [0, 1]
            
                self._control.throttle = round(throttle / 0.05) * 0.05
                self._control.brake = round(brake / 0.2) * 0.2
                self._control.steer = round(max(-0.7, min(steer * 0.7, 0.7)), 1)  # Ensure steer value is within [-0.7, 0.7]
                self._control.hand_brake = hand_brake

            elif self.input_device == 1:
                throttle = self.joystick.get_axis(2)  # Throttle: Axis 2 (Throttle pedal, on the right)
                brake = self.joystick.get_axis(3)     # Brake: Axis 3 (Brake pedal, in the middle)
                steer = self.joystick.get_axis(0)     # Steering: Axis 0 (Wheel)
                hand_brake = self.joystick.get_button(7)  # Handbrake: Button 7 (L2)

                throttle = max(0, min(-0.5 * (throttle - 1), 0.5)) # Ensure throttle value is within [0, 0.5]
                brake = max(0, min(-0.5 * (brake - 1), 1)) # Ensure brake value is within [0, 1]
            
                self._control.throttle = round(throttle / 0.05) * 0.05
                self._control.brake = round(brake / 0.2) * 0.2
                self._control.steer = round(max(-0.7, min(steer, 0.7)), 1)  # Ensure steer value is within [-0.7, 0.7]
                self._control.hand_brake = hand_brake


    @staticmethod
    def _is_quit_shortcut(key):
        return (key == K_ESCAPE) or (key == K_q and pygame.key.get_mods() & KMOD_CTRL)
    
