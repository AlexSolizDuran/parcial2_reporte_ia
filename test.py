import requests
import json

def test_generar_sql():
    """
    Test for the /generar-sql endpoint.
    """
    url = "http://127.0.0.1:8001/generar-sql"
    data = {"prompt": "lista de clientes"}
    
    print(f"▶️  Testing endpoint: {url}")
    print(f"POST data: {data}")

    try:
        response = requests.post(url, json=data)
        
        print(f"Response Status Code: {response.status_code}")
        
        # 1. Check for successful response
        assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
        print("✅ Status code is 200")

        # 2. Check if response is valid JSON
        try:
            response_data = response.json()
            print("✅ Response is valid JSON")
            print("Response content:")
            print(json.dumps(response_data, indent=2))
        except json.JSONDecodeError:
            assert False, "Response is not valid JSON"

        # 3. Check for required fields
        required_keys = ["sql", "formato", "columnas"]
        for key in required_keys:
            assert key in response_data, f"Required key '{key}' is missing from the response"
        print(f"✅ Response contains all required keys: {required_keys}")

        # 4. Check if 'columnas' is a list
        assert isinstance(response_data["columnas"], list), f"'columnas' should be a list, but got {type(response_data['columnas'])}"
        print("✅ 'columnas' field is a list")

        print("\n🎉 All tests passed!")

    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Could not connect to the server.")
        print(f"Make sure the FastAPI server is running on {url}")
        assert False, f"RequestException: {e}"

if __name__ == "__main__":
    test_generar_sql()
