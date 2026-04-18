'''Test module for fillable forms for the job-campaign-tracker Flask app.'''

def test_add_contact_post(seeded_client):
    response = seeded_client.post('/contacts/add',
                                  data = {
                                      'name': 'John Doe',
                                      'org_name': 'Data Policy Center',
                                      'platform': 'LinkedIn',
                                      'contact_value': '/in/jd1984',
                                      'capacity': 'Peer',
                                      'next_follow_up_date': '',
                                      'notes': 'Enthusiastic initial contact, shaky unavailability for follow-up'
                                  })
    assert response.status_code == 302

def test_add_application_post(seeded_client):
    response = seeded_client.post('/applications/add',
                                  data = {
                                      'app_submitted': '04/15/2026',
                                      'org_name': 'Data Policy Center',
                                      'role': 'Research Associate I',
                                      'url': 'https://www.dpc.org/careers',
                                      'referral_contact_id': '',
                                      'status': 'Applied',
                                      'follow_up_date': '',
                                      'notes': ''
                                  })
    assert response.status_code == 302

def test_add_org_post(seeded_client):
    response = seeded_client.post('/orgs/add',
                                  data = {
                                      'name': 'Data Policy Center',
                                      'careers_url': 'https://www.dpc.org/careers',
                                      'category': 'Research & Policy',
                                      # lamp_list is stored as an integer 0,1
                                      'lamp_list': '0',
                                      'notes': ''
                                  })
    assert response.status_code == 302