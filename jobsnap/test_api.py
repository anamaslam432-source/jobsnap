import requests

url = "https://jsearch.p.rapidapi.com/search-v2"
querystring = {"query": "Developer in United States", "page": "1", "num_pages": "1", "country": "us", "date_posted": "all"}
headers = {"x-rapidapi-key": "0abd5fd873msh36038ee65ac10d9p12c138jsn30f6739d2b6a", "x-rapidapi-host": "jsearch.p.rapidapi.com"}

response = requests.get(url, headers=headers, params=querystring)

print("STATUS CODE:", response.status_code)
print("RESPONSE:", response.text[:3000])