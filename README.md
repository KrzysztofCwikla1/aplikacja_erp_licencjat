
## Logowanie

Domyslny uzytkownik: login: admin / hasło: admin123

## Uruchomienie
Komendy należy wykonać w folderze aplikacji np. C:\Users\"nazwa_uzytkownika"\Desktop\erp_app> 

# 1. Instalacja zależności
pip install -r requirements.txt

# 2. Inicjalizacja bazy danych 
python3 database.py

# 3. Uruchomienie serwera
python -m uvicorn main:app --reload --port 8000
# Następnie w pasku wyszukiwania przeglądarki wpisujemy:
 http://127.0.0.1:8000  (przekieruje na /login)
 Dokumentacja API: http://127.0.0.1:8000/docs
