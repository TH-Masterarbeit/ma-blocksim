import json
import simpy
from schema import Schema, SchemaError


class SimulationWorld:
    """The world starts here. It sets the simulation world.

    The simulation world can be configured with the following characteristics:

    :param int sim_duration: duration of the simulation
    :param str blockchain: the type of blockchain being simulated (e.g. bitcoin or ethereum)
    :param dict time_between_block_distribution: Probability distribution to represent the time between blocks
    :param dict validate_tx_distribution: Probability distribution to represent the transaction validation delay
    :param dict validate_block_distribution: Probability distribution to represent the block validation delay

    Each distribution is represented as dictionary, with the following schema:
    ``{ 'name': str, 'parameters': tuple }``

    We use SciPy to work with probability distributions.

    You can see a complete list of distributions here:
    https://docs.scipy.org/doc/scipy/reference/stats.html

    You can use the ``scripts/test-fit-distribution.py`` to find a good distribution and its parameters which fits your input data measured.
    """

    def __init__(self,
                 sim_duration: int,
                 initial_time: int,
                 blockchain: str,
                 measured_latency: str,
                 measured_throughput_received: str,
                 measured_throughput_sent: str,
                 measured_delays: str):
        if isinstance(sim_duration, int) is False:
            raise TypeError(
                'sim_duration needs to be an integer')
        if isinstance(initial_time, int) is False:
            raise TypeError(
                'initial_time needs to be an integer')
        if isinstance(blockchain, str) is False:
            raise TypeError(
                'blockchain needs to be a string')
        self._measured_delays = self._read_json_file(measured_delays)
        self._sim_duration = sim_duration
        self._initial_time = initial_time
        self._blockchain = blockchain
        self._measured_latency = measured_latency
        self._measured_throughput_received = measured_throughput_received
        self._measured_throughput_sent = measured_throughput_sent
        # Set the SimPy Environment
        self._env = simpy.Environment(initial_time=self._initial_time)
        self._set_delays()
        self._set_latencies()
        self._set_throughputs()

    @property
    def blockchain(self):
        return self._blockchain

    @property
    def locations(self):
        return self._locations

    @property
    def env(self):
        return self._env

    def start_simulation(self):
        self._env.run(until=self._sim_duration)

    def _set_delays(self):
        """Injects the probability distribution delays in the environment variable to be
        used during the simulation"""
        self._validate_distribution(
            self._measured_delays['tx_validation'],
            self._measured_delays['block_validation'])
        self._env.delays = dict(
            VALIDATE_TX=self._measured_delays['tx_validation'],
            VALIDATE_BLOCK=self._measured_delays['block_validation'],
            TIME_BETWEEN_BLOCKS=self._measured_delays['time_between_blocks']
        )

    def _set_latencies(self):
        """Reads the file with the latencies measurements taken"""
        data = self._read_json_file(self._measured_latency)
        self._locations = list(data['locations'])
        self._env.delays.update(dict(LATENCIES=data['locations']))

    def _set_throughputs(self):
        """Reads the measured throughputs and pass it to the environment variable to be
        used during the simulation"""
        throughput_received = self._read_json_file(
            self._measured_throughput_received)
        throughput_sent = self._read_json_file(self._measured_throughput_sent)
        # Check if all locations exist
        locations_rcvd = list(throughput_received['locations'])
        locations_sent = list(throughput_sent['locations'])
        if locations_rcvd != self.locations or locations_sent != self.locations:
            raise RuntimeError(
                "The locations in latencies measurements are not equal in throughputs measurements")
        # Pass the throughputs to the environment variable
        self._env.delays.update(dict(
            THROUGHPUT_RECEIVED=throughput_received['locations'],
            THROUGHPUT_SENT=throughput_sent['locations']
        ))

    def _validate_distribution(self, *distributions: dict):
        for distribution in distributions:
            distribution_schema = Schema({
                'name': str,
                'parameters': str
            })
            try:
                distribution_schema.validate(distribution)
            except SchemaError:
                raise TypeError(
                    'Probability distribution must follow this schema: { \'name\': str, \'parameters\': tuple as a string }')

    def _read_json_file(self, file_location):
        with open(file_location) as f:
            return json.load(f)
