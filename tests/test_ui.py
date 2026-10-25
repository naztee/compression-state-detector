from streamlit.testing.v1 import AppTest

def test_dashboard_api_failure_renders(monkeypatch,tmp_path):
    monkeypatch.setenv('DB_PATH',str(tmp_path/'test.sqlite'))
    import data
    def fail(q): raise data.DataError('simulated offline')
    monkeypatch.setattr(data,'search',fail)
    at=AppTest.from_file('../app.py').run(timeout=30)
    assert not at.exception
    assert any('Data unavailable' in e.value for e in at.error)
    for page in ['Market Scanner','State Transition Monitor','Historical State Charts','Data Quality Indicators','Rules & Validation']:
        at.sidebar.radio[0].set_value(page).run(timeout=30)
        assert not at.exception
