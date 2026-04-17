'''Route testing module for the job-campaign-tracker Flask app.'''

def test_dashboard_index(seeded_client):
    response = seeded_client.get('/')
    assert response.status_code == 200

def test_orgs_index(seeded_client):
    response = seeded_client.get('/orgs')
    assert response.status_code == 200

def test_orgs_add(seeded_client):
    response = seeded_client.get('/orgs/add')
    assert response.status_code == 200

def test_orgs_detail(seeded_client):
    response = seeded_client.get('/orgs/1')
    assert response.status_code == 200

def test_contacts_index(seeded_client):
    response = seeded_client.get('/contacts')
    assert response.status_code == 200

def test_contacts_add(seeded_client):
    response = seeded_client.get('/contacts/add')
    assert response.status_code == 200

def test_contacts_detail(seeded_client):
    response = seeded_client.get('/contacts/1')
    assert response.status_code == 200

def test_applications_index(seeded_client):
    response = seeded_client.get('/applications')
    assert response.status_code == 200

def test_applications_add(seeded_client):
    response = seeded_client.get('/applications/add')
    assert response.status_code == 200

def test_applications_detail(seeded_client):
    response = seeded_client.get('/applications/1')
    assert response.status_code == 200