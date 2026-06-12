# BUIA 2026 - Nouzová navigace

Mobilní webová aplikace pro asistenci při evakuaci pomocí AI rozpoznávání polohy z kamery.

## Funkce

- 📷 Používá kameru mobilu pro rozpoznání aktuální polohy
- 🤖 AI model (CNN) trénovaný na fotkách z různých míst budovy
- 🚨 Zobrazuje instrukce pro bezpečný únik podle rozpoznané polohy
- 📱 Mobilní optimalizované rozhraní
- ⚡ Real-time analýza s automatickým opakováním každé 3 sekundy

## Podporované lokace

Aplikace rozpoznává 5 typů lokalit:
- **Učebna**
- **Chodba**
- **Schodiště**
- **Turnikety (Přízemí)**
- **Venek**

## Instalace

### 1. Nastavení virtuálního prostředí

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# nebo
source venv/bin/activate  # Linux/Mac
```

### 2. Instalace závislostí

```bash
pip install -r requirements.txt
```

### 3. Příprava trénovacích dat

Ujistěte se, že složka `fotky/` obsahuje podsložky pro každou lokalitu:
```
fotky/
├── chodba/
├── schodiště/
├── turnikety/
├── učebna/
└── venek/
```

Každá podsložka by měla obsahovat trénovací fotky dané lokality.

### 4. Trénování modelu

```bash
 python ../train_model.py --epochs 50 --batch-size 16 --mixup --fine-tune-epochs 30 --unfreeze-layers 120
```

Tento skript:
- Načte fotky ze složky `fotky/`
- Vytvoří a natrénuje CNN model
- Uloží model jako `NavigationApp/main/location_model.h5`
- Uloží štítky tříd jako `NavigationApp/main/model_labels.pkl`

### 5. Spuštění aplikace

```bash
cd NavigationApp
python manage.py runserver
```

Aplikace bude dostupná na `http://localhost:8000`

## Použití

1. Otevřete aplikaci v mobilním prohlížeči
2. Klikněte na tlačítko "📷 Spustit kameru"
3. Povolte přístup k kameře
4. Aplikace automaticky analyzuje polohu každé 3 sekundy
5. Na obrazovce se zobrazí rozpoznaná lokalita a instrukce pro únik

## Technologie

- **Backend**: Django 6.0
- **AI/ML**: TensorFlow, Keras
- **Frontend**: Vanilla JavaScript, HTML5 Camera API
- **Image Processing**: Pillow, NumPy

## Struktura projektu

```
BUIA_2026_navigationapp/
├── NavigationApp/
│   ├── main/
│   │   ├── escape_instructions.py    # Mapování lokalit na instrukce
│   │   ├── views.py                  # Django views s API pro klasifikaci
│   │   ├── urls.py                   # URL routing
│   │   ├── templates/
│   │   │   └── main/
│   │   │       └── homepage.html     # Mobilní rozhraní s kamerou
│   │   └── static/
│   │       └── main/
│   │           └── camera.js         # JavaScript pro kameru a API
│   └── NavigationApp/
│       └── settings.py               # Django nastavení
├── fotky/                            # Trénovací data
├── train_model.py                    # Skript pro trénování modelu
└── requirements.txt                  # Python závislosti
```

## API Endpoint

### POST /api/classify/

Přijme obrázek z kamery a vrátí rozpoznanou lokalitu s instrukcemi.

**Request**: multipart/form-data s polem `image`

**Response**:
```json
{
  "location": "Učebna",
  "location_key": "ucebna",
  "instruction": "Opustite ucebnu a otocte se do leva, pokracujte rovne ke schodisti",
  "confidence": 0.95
}
```

## Poznámky

- Aplikace vyžaduje HTTPS pro přístup k kameře v produkci
- Model je optimalizován pro mobilní zařízení
- Pro lepší výsledky přidejte více trénovacích fotek do každé složky
- Výchozí nastavení trénování: 20 epoch, batch size 32, obrázky 224x224

## Licence

Projekt pro BUIA 2026