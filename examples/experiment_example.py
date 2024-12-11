from bioexperiment_suite.experiment import Experiment  # Import the Experiment class
from bioexperiment_suite.tools import get_connected_devices  # Import the get_connected_devices function

# Define the experiment parameters
TOTAL_EXPERIMENT_DURATION_HOURS = 24  # Total duration of the experiment in hours
SOLUTION_REFRESH_INTERVAL_MIN = 60  # Interval for refreshing the solution in minutes

MEASUREMENT_INTERVAL_MINUTES = 5  # Interval for taking measurements in minutes
POURED_OUT_VOLUME_ML = 2  # Volume of solution poured out in mL
INFUSED_VOLUME_ML = 1  # Volume of solution infused in mL
FLOW_RATE_ML_PER_MINUTE = 3  # Flow rate of the pump in mL/min

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
)  # Number of solution refreshes
n_measurements_per_solution_refresh = (
    SOLUTION_REFRESH_INTERVAL_MIN // MEASUREMENT_INTERVAL_MINUTES
)  # Number of measurements per refresh

# Retrieve connected devices by checking the serial ports
pumps, spectrophotometers = get_connected_devices()

# Unpack discovered devices
(pump1, pump2) = pumps  # Suppose we have two pumps
(spectrophotometer,) = spectrophotometers  # Suppose we have one spectrophotometer

# Initialize the experiment
experiment = Experiment()

# Configure the experiment with measurements and actions
for i in range(n_solution_refreshes):  # Loop over the number of solution refreshes
    for j in range(n_measurements_per_solution_refresh):  # Loop over the number of measurements per refresh
        experiment.add_measurement(
            spectrophotometer.get_temperature, measurement_name="Temperature (C)"
        )  # Measure temperature
        experiment.add_measurement(
            spectrophotometer.measure_absorbance, measurement_name="Absorbance"
        )  # Measure absorbance
        experiment.add_wait(MEASUREMENT_INTERVAL_MINUTES * 60)  # Wait for the measurement interval

    # Add actions to refresh the solution
    experiment.add_action(
        pump2.pour_in_volume, volume=POURED_OUT_VOLUME_ML, flow_rate=FLOW_RATE_ML_PER_MINUTE, direction="left"
    )  # Pour out the old solution
    experiment.add_action(
        pump1.pour_in_volume, volume=INFUSED_VOLUME_ML, flow_rate=FLOW_RATE_ML_PER_MINUTE, direction="right"
    )  # Infuse the new solution
    experiment.add_wait(MEASUREMENT_INTERVAL_MINUTES * 60)  # Wait after refreshing the solution

# Run the experiment
experiment.run()

# After the experiment is complete, the results can be accessed from the experiment object by assigned names
print(experiment.measurements["Temperature (C)"])
print(experiment.measurements["Absorbance"])
