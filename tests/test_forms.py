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