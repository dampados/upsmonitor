import pytest
from custom_types import ActionBoxMock, Inputs, PowerState, PowerStateName
from repository import react, STATE_MAPPING

class TestReact:
    def test_new_data_resets_counter_and_updates_values(self):
        """When new data arrives (not None), counter resets and values update."""
        old = PowerState(
            status=PowerStateName.UNKNOWN,
            ticks_counter=59,
            canary_latest_bool=True,
            switches_latest_bool=True
        )
        
        i = Inputs(canary_healthy=False, switches_healthy=None)
        mock = ActionBoxMock()
        new = react(old, i, mock)
        
        assert new.ticks_counter == 0
        assert new.canary_latest_bool is False
        assert new.switches_latest_bool is True
        assert new.status == PowerStateName.UNKNOWN
        assert mock.current_routine is mock.start_restoring_routine  # default, unchanged

    def test_silence_below_threshold_increments_counter_no_action(self):
        """Silence (None, None) below 60 ticks just increments counter."""
        old = PowerState(
            status=PowerStateName.UNKNOWN,
            ticks_counter=59,
            canary_latest_bool=True,
            switches_latest_bool=True
        )
        
        i = Inputs(canary_healthy=None, switches_healthy=None)
        mock = ActionBoxMock()
        new = react(old, i, mock)
        
        assert new.ticks_counter == 60
        assert new.status == PowerStateName.UNKNOWN
        assert mock.current_routine is mock.start_restoring_routine  # default, unchanged

    def test_silence_at_threshold_triggers_state_change_and_calls_action(self):
        """At 60 ticks of silence, state changes and ActionBox is called."""
        old = PowerState(
            status=PowerStateName.UNKNOWN,
            ticks_counter=60,
            canary_latest_bool=True,
            switches_latest_bool=True
        )
        
        i = Inputs(canary_healthy=None, switches_healthy=None)
        mock = ActionBoxMock()
        new = react(old, i, mock)
        
        assert new.status == PowerStateName.OK_HEALTHY
        assert new.ticks_counter == 0
        assert mock.current_routine is mock.start_restoring_routine

    def test_silence_at_threshold_with_bad_on_bbu_calls_suspend(self):
        """BAD_ON_BBU triggers suspend, not restore."""
        old = PowerState(
            status=PowerStateName.UNKNOWN,
            ticks_counter=60,
            canary_latest_bool=False,
            switches_latest_bool=False
        )
        
        i = Inputs(canary_healthy=None, switches_healthy=None)
        mock = ActionBoxMock()
        new = react(old, i, mock)
        
        assert new.status == PowerStateName.BAD_ON_BBU
        assert new.ticks_counter == 0
        assert mock.current_routine is mock.start_suspending_routine

    @pytest.mark.parametrize("canary,switches,expected_status", [
        (False, False, PowerStateName.BAD_ON_BBU),
        (False, True, PowerStateName.BAD_CANARY_DEAD),
        (True, True, PowerStateName.OK_HEALTHY),
        (True, False, PowerStateName.OK_GENERATOR),
    ])
    def test_all_state_mappings_trigger_correct_action(self, canary, switches, expected_status):
        """All 4 mappings produce correct state and call correct ActionBox method."""
        old = PowerState(
            status=PowerStateName.UNKNOWN,
            ticks_counter=60,
            canary_latest_bool=canary,
            switches_latest_bool=switches
        )
        
        i = Inputs(canary_healthy=None, switches_healthy=None)
        mock = ActionBoxMock()
        new = react(old, i, mock)
        
        assert new.status == expected_status
        assert new.ticks_counter == 0
        
        if expected_status == PowerStateName.BAD_ON_BBU:
            assert mock.current_routine is mock.start_suspending_routine
        else:
            assert mock.current_routine is mock.start_restoring_routine

    def test_start_from_unknown_increments_counter(self):
        """Starting from UNKNOWN doesn't trigger action until counter reaches 60."""
        old = PowerState(
            status=PowerStateName.UNKNOWN,
            ticks_counter=0,
            canary_latest_bool=True,
            switches_latest_bool=True
        )
        
        i = Inputs(canary_healthy=None, switches_healthy=None)
        mock = ActionBoxMock()
        new = react(old, i, mock)
        
        assert new.status == PowerStateName.UNKNOWN
        assert new.ticks_counter == 1
        assert mock.current_routine is mock.start_restoring_routine  # default, unchanged

    def test_mixed_inputs_canary_only_updates_canary(self):
        """When only canary changes, switches value stays unchanged."""
        old = PowerState(
            status=PowerStateName.UNKNOWN,
            ticks_counter=60,
            canary_latest_bool=True,
            switches_latest_bool=True
        )
        
        i = Inputs(canary_healthy=False, switches_healthy=None)
        mock = ActionBoxMock()
        new = react(old, i, mock)
        
        assert new.canary_latest_bool is False
        assert new.switches_latest_bool is True
        assert new.ticks_counter == 0
        assert new.status == PowerStateName.UNKNOWN
        assert mock.current_routine is mock.start_restoring_routine  # default, unchanged

    def test_mixed_inputs_switches_only_updates_switches(self):
        """When only switches changes, canary value stays unchanged."""
        old = PowerState(
            status=PowerStateName.UNKNOWN,
            ticks_counter=60,
            canary_latest_bool=True,
            switches_latest_bool=True
        )
        
        i = Inputs(canary_healthy=None, switches_healthy=False)
        mock = ActionBoxMock()
        new = react(old, i, mock)
        
        assert new.canary_latest_bool is True
        assert new.switches_latest_bool is False
        assert new.ticks_counter == 0
        assert new.status == PowerStateName.UNKNOWN
        assert mock.current_routine is mock.start_restoring_routine  # default, unchanged

    def test_silence_after_counter_reset_restarts_counting(self):
        """After new data resets counter, silence starts counting again."""
        old = PowerState(
            status=PowerStateName.UNKNOWN,
            ticks_counter=0,
            canary_latest_bool=True,
            switches_latest_bool=True
        )
        
        i = Inputs(canary_healthy=None, switches_healthy=None)
        mock = ActionBoxMock()
        new = react(old, i, mock)
        
        assert new.ticks_counter == 1
        assert new.status == PowerStateName.UNKNOWN
        assert mock.current_routine is mock.start_restoring_routine  # default, unchanged

    def test_repeated_silence_after_threshold_does_not_trigger_twice(self):
        """After state change, silence doesn't trigger again without counter reset."""
        old = PowerState(
            status=PowerStateName.OK_HEALTHY,
            ticks_counter=60,
            canary_latest_bool=True,
            switches_latest_bool=True
        )
        
        i = Inputs(canary_healthy=None, switches_healthy=None)
        mock = ActionBoxMock()
        new = react(old, i, mock)
        
        assert new.ticks_counter == 0
        assert new.status == PowerStateName.OK_HEALTHY
        assert mock.current_routine is mock.start_restoring_routine  # default, unchanged