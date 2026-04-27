from bioexperiment_suite.experiment import Experiment  # Import the Experiment class
from bioexperiment_suite.interfaces import LabDevicesClient

# Define the experiment parameters
TOTAL_EXPERIMENT_DURATION_HOURS = 24  # Total duration of the experiment in hours
SOLUTION_REFRESH_INTERVAL_MIN = 60  # Interval for refreshing the solution in minutes

MEASUREMENT_INTERVAL_MINUTES = 5  # Interval for taking measurements in minutes
POURED_OUT_VOLUME_ML = 2  # Volume of solution poured out in mL
INFUSED_VOLUME_ML = 1  # Volume of solution infused in mL
FLOW_RATE_ML_PER_MINUTE = 3  # Flow rate of the pump in mL/min

LAB_DEVICES_PORT = 9001  # Per-lab-machine chisel-tunnel port

# Ensure intervals are valid
assert (
    SOLUTION_REFRESH_INTERVAL_MIN % MEASUREMENT_INTERVAL_MINUTES == 0
), "Solution refresh interval should be a multiple of measurement interval"
assert (
    TOTAL_EXPERIMENT_DURATION_HOURS * 60
) % SOLUTION_REFRESH_INTERVAL_MIN == 0, "Total experiment duration should be a multiple of solution refresh interval"

# Calculate the number of solution refreshes and measurements per refresh
n_solution_refreshes = (
    TOTAL_EXPERIMENT_DURATION_HOURS * 60 // SOLUTION_REFRESH_INTERVAL_MIN
)
n_measurements_per_solution_refresh = (
    SOLUTION_REFRESH_INTERVAL_MIN // MEASUREMENT_INTERVAL_MINUTES
)

# Connect to the lab devices service and discover devices
client = LabDevicesClient(port=LAB_DEVICES_PORT)
devices = client.discover()

# Unpack discovered devices
(pump1, pump2) = devices.pumps  # Suppose we have two pumps
(densitometer,) = devices.densitometers  # Suppose we have one densitometer

# Initialize the experiment
experiment = Experiment()

# Configure the experiment with measurements and actions
for i in range(n_solution_refreshes):
    for j in range(n_measurements_per_solution_refresh):
        experiment.add_measurement(
            densitometer.get_temperature, measurement_name="Temperature (C)"
        )
        experiment.add_measurement(
            densitometer.measure_optical_density, measurement_name="Optical density"
        )
        experiment.add_wait(MEASUREMENT_INTERVAL_MINUTES * 60)

    experiment.add_action(
        pump2.pour_in_volume, volume=POURED_OUT_VOLUME_ML, flow_rate=FLOW_RATE_ML_PER_MINUTE, direction="left"
    )
    experiment.add_action(
        pump1.pour_in_volume, volume=INFUSED_VOLUME_ML, flow_rate=FLOW_RATE_ML_PER_MINUTE, direction="right"
    )
    experiment.add_wait(MEASUREMENT_INTERVAL_MINUTES * 60)

# Run the experiment
experiment.start()

# After the experiment is complete, the results can be accessed from the experiment object by assigned names
print(experiment.measurements["Temperature (C)"])
print(experiment.measurements["Optical density"])
