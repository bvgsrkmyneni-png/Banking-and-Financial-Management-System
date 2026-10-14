import importlib
import pytest

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('BTMS_DB',str(tmp_path/'test.db'))
    import app
    importlib.reload(app)
    app.app.config.update(TESTING=True)
    with app.app.test_client() as c: yield c

def login(c,number='10010001',pin='1234'):
    return c.post('/api/login',json={'number':number,'pin':pin})

def test_authentication(client):
    assert client.get('/api/me').status_code==401
    assert login(client,pin='0000').status_code==401
    assert login(client).status_code==200
    assert client.get('/api/me').json['account']['balance']=='25000.00'

def test_transfer_and_history(client):
    login(client)
    assert client.post('/api/transfer',json={'destination':'10010002','amount':'500'}).status_code==200
    assert client.get('/api/me').json['account']['balance']=='24500.00'
    assert client.get('/api/history').json['items'][0]['kind']=='transfer'
    client.post('/api/logout');login(client,'10010002','2345')
    assert client.get('/api/me').json['account']['balance']=='19000.00'

def test_invalid_transfer_is_atomic(client):
    login(client)
    assert client.post('/api/transfer',json={'destination':'10010002','amount':'999999'}).status_code==400
    assert client.post('/api/transfer',json={'destination':'999','amount':'1'}).status_code==400
    assert client.get('/api/me').json['account']['balance']=='25000.00'
    assert client.get('/api/history').json['items']==[]

def test_deposit_withdraw_and_validation(client):
    login(client)
    assert client.post('/api/deposit',json={'amount':'10.50'}).status_code==200
    assert client.post('/api/withdraw',json={'amount':'0.001'}).status_code==400
    assert client.post('/api/withdraw',json={'amount':'10.50'}).status_code==200
    assert client.get('/api/me').json['account']['balance']=='25000.00'

def test_account_create_update_audit(client):
    login(client)
    response=client.post('/api/accounts',json={'name':'Demo Student','pin':'9876'})
    assert response.status_code==201
    assert client.patch('/api/account',json={'name':'Updated Student'}).status_code==200
    assert client.get('/api/audit').json['passed'] is True
    client.post('/api/logout')
    assert login(client,response.json['number'],'9876').status_code==200
