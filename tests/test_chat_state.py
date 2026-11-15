"""Don Surco state transitions; no API calls and no credentials required."""
import unittest
from utils.ai_chat import ChatEvent
from utils.chat_state import ChatSession, MAX_PROMPT

class ChatStateTests(unittest.TestCase):
    def test_steps_and_final_are_streamed_once_and_history_is_clean(self):
        state=ChatSession()
        self.assertTrue(state.begin('Mi parcela','request-1','priorities'))
        self.assertFalse(state.begin('Otra pregunta','request-2','priorities'))
        state.iterator=iter([ChatEvent('tool',label='Consultando humedad',payload={'humedad':22}),ChatEvent('final',payload='Respuesta del modelo')])
        state.advance()
        self.assertTrue(state.busy)
        self.assertEqual(len(state.messages[-1]['steps']),1)
        state.advance()
        self.assertFalse(state.busy)
        self.assertEqual(state.messages[-1]['content'],'Respuesta del modelo')
        self.assertFalse(state.begin('Duplicada','request-1','priorities'))
        self.assertEqual(state.history(),[{'role':'user','content':'Mi parcela'},{'role':'assistant','content':'Respuesta del modelo'}])

    def test_errors_do_not_enter_the_model_history(self):
        state=ChatSession()
        state.begin('Pregunta','id','context')
        state.iterator=iter([ChatEvent('error',payload='Private provider error detail')])
        state.advance()
        self.assertFalse(state.busy)
        self.assertNotIn('Private',state.messages[-1]['content'])
        self.assertEqual(state.history(),[{'role':'user','content':'Pregunta'}])

    def test_input_limits_and_context_cancellation(self):
        state=ChatSession()
        self.assertFalse(state.begin('   ','id','context'))
        self.assertFalse(state.begin('a'*(MAX_PROMPT+1),'id','context'))
        self.assertTrue(state.begin('Estado','id','context'))
        state.cancel()
        self.assertFalse(state.busy)
        self.assertTrue(state.messages[-1]['error'])
        self.assertEqual(state.history(),[{'role':'user','content':'Estado'}])

    def test_a_failed_generator_finishes_cleanly(self):
        def fail():
            raise RuntimeError('server detail')
            yield
        state=ChatSession()
        state.begin('Estado','id','context')
        state.iterator=fail()
        state.advance()
        self.assertFalse(state.busy)
        self.assertTrue(state.messages[-1]['error'])

class ChatWidgetIntegrationTests(unittest.TestCase):
    def test_streaming_and_plot_history_in_streamlit(self):
        from unittest.mock import patch
        from streamlit.testing.v1 import AppTest
        script = """
import streamlit as st
from utils.types import FarmerPriorities
from components.chat_widget import render_chat
st.session_state.data_mode = 'legacy'
if 'selected_plot_id' not in st.session_state:
    st.session_state.selected_plot_id = 'lote-norte'
    st.session_state.farmer_priorities = FarmerPriorities()
render_chat()
"""
        from components.chat_widget import _COMPONENT as real_component
        render_order = []
        def mount_panel(*args, **kwargs):
            render_order.append("panel")
            return real_component(*args, **kwargs)
        def fake_turn(history, plot_id):
            render_order.append("model")
            yield ChatEvent('tool', label='Consultando humedad', payload={'humedad':22})
            yield ChatEvent('final', payload='Respuesta simulada para ' + plot_id)
        with patch('components.chat_widget._available', return_value=True), patch(
            'components.chat_widget.ai_chat.run_chat_turn', side_effect=fake_turn
        ) as runner, patch('components.chat_widget._COMPONENT', side_effect=mount_panel):
            at = AppTest.from_string(script, default_timeout=15).run()
            state = at.session_state['don_surco_conversations']['lote-norte']
            self.assertTrue(state.begin('Pregunta', 'request-test', repr(at.session_state['farmer_priorities'])))
            render_order.clear()
            at.run()
            self.assertEqual(render_order[:2], ["panel", "model"])
            self.assertTrue(state.busy)
            self.assertEqual(len(state.messages[-1]['steps']), 1)
            at.run()
            self.assertFalse(state.busy)
            self.assertFalse(at.exception)
            self.assertEqual(state.messages[-1]['content'], 'Respuesta simulada para lote-norte')
            runner.assert_called_once()
            at.session_state['selected_plot_id'] = 'lote-sur'
            at.run()
            self.assertEqual(at.session_state['don_surco_conversations']['lote-sur'].messages, [])
            at.session_state['selected_plot_id'] = 'lote-norte'
            at.run()
            self.assertEqual(at.session_state['don_surco_conversations']['lote-norte'].messages[-1]['content'], 'Respuesta simulada para lote-norte')

if __name__=='__main__': unittest.main()
