from app import create_app
app = create_app()
with app.test_client() as client:
    response = client.get('/login')
    print(f'Status: {response.status_code}')
    if response.status_code != 200:
        print(f'Error: {response.data.decode()[:500]}')
