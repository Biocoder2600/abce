from collections import deque, defaultdict
import traceback
from time import sleep
import random


def _get_methods(agent_class):
    return set(method
               for method in dir(agent_class)
               if callable(getattr(agent_class, method)) and
               method[0] != '_' and method != 'init')


class Group(object):
    def __init__(self, sim, processorgroup, group_names, agent_classes, ids=None, agent_arguments=None):
        self.sim = sim
        self.num_managers = sim.processes
        self._agents = processorgroup
        self.group_names = group_names
        self.agent_classes = agent_classes
        self._agent_arguments    = agent_arguments
        for method in set.intersection(*(_get_methods(agent_class) for agent_class in agent_classes)):
            setattr(self, method,
                    eval('lambda self=self, *argc, **kw: self.do("%s", *argc, **kw)' %
                         method))

        self.panel_serial = 0
        self.last_action = "Begin_of_Simulation"

        if len(group_names) == 1:
            self.free_ids = defaultdict(deque)
            if group_names[0] not in self._agents.agents:
                self._agents.new_group(group_names[0])
        if ids is None:
            self._ids = [[]]
        else:
            self._ids = ids

    def __add__(self, other):
        return Group(self.sim, self._agents, self.group_names + other.group_names, self.agent_classes + other.agent_classes, self._ids + other._ids)

    def __radd__(self, g):
        if isinstance(g, Group):
            return self.__add__(g)
        else:
            return self

    def panel_log(self, variables=[], possessions=[], func={}, len=[]):
        """ panel_log(.) writes a panel of variables and possessions
        of a group of agents into the database, so that it is displayed
        in the gui.

        Args:
            possessions (list, optional):
                a list of all possessions you want to track as 'strings'
            variables (list, optional):
                a list of all variables you want to track as 'strings'
            func (dict, optional):
                accepts lambda functions that execute functions. e.G.
                :code:`func = lambda self: self.old_money - self.new_money`
            len (list, optional):
                records the length of the list or dictionary with that name.

        Example in start.py::

            for round in simulation.next_round():
                firms.produce_and_sell()
                firms.panel_log(possessions=['money', 'input'],
                            variables=['production_target', 'gross_revenue'])
                households.buying()
        """
        self.do('_panel_log', variables, possessions, func, len, self.last_action)

    def agg_log(self, variables=[], possessions=[], func={}, len=[]):
        """ agg_log(.) writes a aggregate data of variables and possessions
        of a group of agents into the database, so that it is displayed
        in the gui.

        Args:
            possessions (list, optional):
                a list of all possessions you want to track as 'strings'
            variables (list, optional):
                a list of all variables you want to track as 'strings'
            func (dict, optional):
                accepts lambda functions that execute functions. e.G.
                :code:`func = lambda self: self.old_money - self.new_money`
            len (list, optional):
                records the length of the list or dictionary with that name.

        Example in start.py::

            for round in simulation.next_round():
                firms.produce_and_sell()
                firms.agg_log(possessions=['money', 'input'],
                            variables=['production_target', 'gross_revenue'])
                households.buying()
        """
        self.do('_agg_log', variables, possessions, func, len)

    def append(self, simulation_parameters, agent_parameters):
        """ Append a new agent to this group. Works only for non-combined groups

        Args:
            simulation_parameters:
                A dictionary of simulation_parameters

            agent_parameters:
                A dictionary of simulation_parameters
        """
        assert len(self.group_names) == 1, 'Group is a combined group, no appending permitted'
        if self.free_ids[self.group_names[0]]:
            id = self.free_ids[self.group_names[0]].popleft()
        else:
            id = len(self._agents.agents[self.group_names[0]])
            self._agents.agents[self.group_names[0]].append(None)
            self._ids[0].append(id)
        Agent = self.agent_classes[0]
        agent = Agent(id, simulation_parameters, agent_parameters, **self._agent_arguments)
        agent.init(simulation_parameters, agent_parameters)
        self._agents.agents[self.group_names[0]][id] = agent
        self._ids[0][id] = id
        return id

    def do(self, command, *args, **kwargs):
        self.last_action = command
        rets = []
        for agent in self._agents.get_agents(self.group_names, self._ids):
            ret = agent._execute(command, args, kwargs)
            rets.append(ret)
        for agent in self._agents.get_agents(self.group_names, self._ids):
            agent._post_messages(self._agents)
        return rets

    def delete_agent(self, id):
        assert len(self.group_names) == 1
        self._agents.agents[self.group_names[0]][id] = None
        self._ids[0][id] = None
        self.free_ids[self.group_names[0]].append(id)

    def name(self):
        return (self.group, self.batch)

    def execute_advance_round(self, time):
        for agent in self._agents.get_agents(self.group_names, self._ids):
            try:
                agent._advance_round(time)
            except KeyboardInterrupt:
                return None
            except AttributeError:
                pass
            except Exception:
                sleep(random.random())
                traceback.print_exc()
                raise Exception()

    def __getitem__(self, *ids):
        if isinstance(*ids, int):
            ids = [ids]
        return Group(self.sim, self._agents, self.group_names, self.agent_classes, ids=ids * len(self.group_names))

    def __len__(self):
        """ Returns the length of a group """
        return sum([1 for agent in self._agents.get_agents(self.group_names, self._ids) if agent is not None])

    def __repr__(self):
        return repr(self)
