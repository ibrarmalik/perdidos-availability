import requests
import json
import re
from datetime import datetime, timedelta
from fpdf import FPDF

# Configuration
START_DATE = datetime(2026, 7, 26)
END_DATE = datetime(2026, 8, 2)
HEADERS = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
}

def get_date_range():
    current = START_DATE
    while current <= END_DATE:
        yield current
        current += timedelta(days=1)

def format_date(dt):
    return dt.strftime('%Y-%m-%d')

class PDFReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.cell(0, 10, 'Informe de Disponibilitat: La Alta Ruta de los Perdidos', align='C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Pàgina {self.page_no()}', align='C')

def create_pdf(results, filename="availability.pdf"):
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_font("helvetica", size=10)
    
    # Table Header
    headers = ["Data", "Pineta", "Góriz (Ref)", "Góriz (Acam)", "Espuguettes", "Bayssellance", "Serradets"]
    col_widths = [25, 20, 25, 25, 25, 25, 25]
    
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("helvetica", 'B', 8) # Smaller font for headers
    
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1, fill=True, align='C')
    pdf.ln()
    
    # Table Rows
    pdf.set_font("helvetica", size=8) # Smaller font for content
    pdf.set_fill_color(255, 255, 255)
    
    for row in results:
        # row structure from main: [d_str, pineta, goriz_ref, goriz_camp, esp, bay, ser]
        for i, item in enumerate(row):
            text = str(item)
            pdf.cell(col_widths[i], 10, text, border=1, align='C')
        pdf.ln()
        
    pdf.output(filename)
    print(f"PDF guardat a {filename}")

def get_pineta():
    print("Fetching Pineta...")
    url = 'https://api.alberguesyrefugios.com/refugios/get/7/getPlazas2/'
    try:
        resp = requests.get(url, headers=HEADERS)
        data = resp.json()
        
        availability_map = {}
        if 'result' in data:
            for room_id, room_data in data['result'].items():
                plazas = room_data.get('plazas', {})
                for date_str, info in plazas.items():
                    # USE 'plazas' field, not 'plazasDisponibles'
                    if info['plazas'] is not None:
                         availability_map[date_str] = availability_map.get(date_str, 0) + int(info['plazas'])
        
        return availability_map
    except Exception as e:
        print(f"Error fetching Pineta: {e}")
        return {}

def get_goriz():
    print("Fetching Goriz...")
    url = 'https://api.alberguesyrefugios.com/refugios/get/5/getPlazas2/'
    try:
        resp = requests.get(url, headers=HEADERS)
        data = resp.json()
        
        # Structure: date -> {'refugio': 0, 'acampada': 0}
        availability_map = {}
        
        if 'result' in data:
            for room_id, room_data in data['result'].items():
                room_name = room_data.get('nombre', '').lower()
                is_acampada = 'acampada' in room_name
                
                plazas = room_data.get('plazas', {})
                for date_str, info in plazas.items():
                    # USE 'plazas' field, not 'plazasDisponibles'
                    if info['plazas'] is not None:
                        count = int(info['plazas'])
                        
                        if date_str not in availability_map:
                            availability_map[date_str] = {'refugio': 0, 'acampada': 0}
                        
                        if is_acampada:
                            availability_map[date_str]['acampada'] += count
                        else:
                            availability_map[date_str]['refugio'] += count
                            
        return availability_map
    except Exception as e:
        print(f"Error fetching Goriz: {e}")
        return {}

def get_espuguettes_day(target_date):
    # Fetch single day for Espuguettes since bulk endpoint is unknown/unreliable
    date_str = target_date.strftime('%d/%m/%Y')
    print(f"Fetching Espuguettes for {date_str}...")
    # Use the id 101245 from the curl
    url = f'https://etape-rest.for-system.com/index.aspx/index.aspx?ref=json-produit-refuge&q=es,101245,{date_str},1'
    
    try:
        resp = requests.get(url, headers=HEADERS)
        text = resp.text
        
        # The response is wrapped in a jQuery callback: jQuery...({...})
        # We can strip the wrapper or just find the JSON object.
        # It starts with { and ends with }
        
        # Simple extraction: find first { and last }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            data = json.loads(json_str)
            
            # Navigate to nbPlacesDispos: refuge -> nbPlacesDispos
            if 'refuge' in data and 'nbPlacesDispos' in data['refuge']:
                return data['refuge']['nbPlacesDispos']
                
        return "Error"
    except Exception as e:
        print(f"Error fetching Espuguettes for {date_str}: {e}")
        return "Error"

def get_bayssellance():
    print("Fetching Bayssellance...")
    url = 'https://centrale.ffcam.fr/index.php?'
    
    # specific headers for this one
    headers = HEADERS.copy()
    headers.update({
        'origin': 'https://centrale.ffcam.fr',
        'referer': 'https://centrale.ffcam.fr/index.php?structure=BK_STRUCTURE%3A107&mode=FORM&_lang=FR',
        'content-type': 'application/x-www-form-urlencoded'
    })

    # Data from curl
    data_payload = {
        'action': 'availability',
        'structure': 'BK_STRUCTURE:107',
        'productCategory': 'BK_PRODUCTCATEGORY:NUITEE',
        'pax': '8' 
    }
    
    try:
        resp = requests.post(url, headers=headers, data=data_payload)
        text = resp.text
        
        # Use re.DOTALL just in case the JSON spans lines
        match = re.search(r'BK\.availability\s*=\s*({.*?});', text, re.DOTALL)
        if match:
            json_str = match.group(1)
            # keys might be unquoted in some JS objects, but usually valid JSON in these variables.
            # If standard json.loads fails, it might be relaxed JSON.
            try:
                data = json.loads(json_str)
                return data
            except json.JSONDecodeError:
                print("Bayssellance returned valid JS but invalid JSON")
                return {}
        else:
            print("Could not find BK.availability in Bayssellance response")
            return {}
    except Exception as e:
        print(f"Error fetching Bayssellance: {e}")
        return {}

def get_serradets():
    print("Fetching Serradets (Brèche de Roland)...")
    url = 'https://centrale.ffcam.fr/index.php?'
    
    headers = HEADERS.copy()
    headers.update({
        'origin': 'https://centrale.ffcam.fr',
        'referer': 'https://centrale.ffcam.fr/index.php?structure=112&mode=FORM&_lang=FR',
        'content-type': 'application/x-www-form-urlencoded'
    })
    
    data_payload = {
        'action': 'availability',
        'structure': 'BK_STRUCTURE:112',
        'productCategory': 'BK_PRODUCTCATEGORY:NUITEE',
        'pax': '8'
    }
    
    try:
        resp = requests.post(url, headers=headers, data=data_payload)
        text = resp.text
        
        match = re.search(r'BK\.availability\s*=\s*({.*?});', text, re.DOTALL)
        if match:
            json_str = match.group(1)
            try:
                data = json.loads(json_str)
                return data
            except json.JSONDecodeError:
                print("Serradets returned valid JS but invalid JSON")
                return {}
        else:
            print("Could not find BK.availability in Serradets response")
            return {}
    except Exception as e:
        print(f"Error fetching Serradets: {e}")
        return {}

def get_bujaruelo(target_date):
    # Bujaruelo API seems to return data for the requested range.
    d_str = target_date.strftime('%Y-%m-%d')
    next_d = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    url = f'https://booking.hotelgest.com/v4/api/?task=price&pcode=278&fromDate={d_str}&toDate={next_d}&promocode='
    
    try:
        resp = requests.get(url, headers=HEADERS)
        data = resp.json()
        
        rooms_summary = []
        
        # data is a dict where keys are room IDs
        for room_id, room_info in data.items():
            if isinstance(room_info, dict):
                # availability at room level
                availability = int(room_info.get('availability', 0))
                
                # find occupancy from the first rate
                occupancy = 0
                rates = room_info.get('rate', {})
                if rates:
                    # just take the first one
                    first_rate_key = next(iter(rates))
                    first_rate = rates[first_rate_key]
                    occupancy = int(first_rate.get('occupancy', 0))
                
                if availability > 0:
                    rooms_summary.append(f"{availability}x{occupancy}p")
                
        return ", ".join(rooms_summary) if rooms_summary else "0"
    except Exception as e:
        print(f"Error fetching Bujaruelo for {d_str}: {e}")
        return "Error"

def main():
    print("Començant la comprovació de disponibilitat per a La Alta Ruta de los Perdidos")
    print(f"Dates: {START_DATE.strftime('%Y-%m-%d')} a {END_DATE.strftime('%Y-%m-%d')}\n")

    # Fetch bulk data where possible
    pineta_data = get_pineta()
    goriz_data = get_goriz()
    # espuguettes_data = get_espuguettes() # We will fetch per day now
    bayssellance_data = get_bayssellance()
    serradets_data = get_serradets()
    
    dates = list(get_date_range())
    
    # Prepare results table for PDF
    results = [] 

    print("\nProcessant dates...")
    
    output_md = "# Informe de Disponibilitat\n\n"
    output_md += "| Data | Pineta | Góriz (Refugi) | Góriz (Acampada) | Espuguettes | Bayssellance | Serradets |\n"
    output_md += "|------|--------|----------------|------------------|-------------|--------------|-----------|\n"
    
    for d in dates:
        d_str = format_date(d)
        
        # Pineta
        pineta = pineta_data.get(d_str, "N/A")
        
        # Goriz
        goriz_info = goriz_data.get(d_str, {'refugio': 'N/A', 'acampada': 'N/A'})
        goriz_ref = goriz_info.get('refugio', 'N/A')
        goriz_camp = goriz_info.get('acampada', 'N/A')
        
        # Espuguettes - fetch individual day
        esp = get_espuguettes_day(d)
        if esp is None: esp = "Sense Info"
        
        # Bayssellance
        bay = bayssellance_data.get(d_str, "N/A")
        if bay is None: bay = "Sense Info"
        
        # Serradets
        ser = serradets_data.get(d_str, "N/A")
        if ser is None: ser = "Sense Info"
        
        # Collect for PDF
        results.append([d_str, pineta, goriz_ref, goriz_camp, esp, bay, ser])
        
        row = f"| {d_str} | {pineta} | {goriz_ref} | {goriz_camp} | {esp} | {bay} | {ser} |"
        output_md += row + "\n"
        print(f"Processat {d_str}")

    print("\n" + output_md)
    
    with open("availability.md", "w") as f:
        f.write(output_md)
    print("\nInforme guardat a availability.md")
    
    # Generate PDF
    create_pdf(results)

if __name__ == "__main__":
    main()
