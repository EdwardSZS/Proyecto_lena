import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import time
import io

#driver = webdriver.Chrome()  # Asegúrate de tener el controlador Chrome o usa el de tu navegador preferido
states= []
delivery_dates=[]
incidents_desc=[]
incidents_date =[]
# Función para construir la URL e iniciar el scraping
def create_headless_driver():
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-gpu")  # Disable GPU acceleration
    options.add_argument("--no-sandbox")  # Bypass OS security model
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    driver = webdriver.Chrome(options=options)
    return driver

driver = create_headless_driver()
def scrape_status(guide_number):
    url = f"https://www.deprisa.com//Tracking/?track={guide_number}"  # Cambia la URL según tus necesidades
    driver.get(url)
    time.sleep(4)  # Espera a que cargue la página, ajusta el tiempo si es necesario

    try:  # //#seccionEstado
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "active-final")))
        state_element = driver.find_elements(By.CLASS_NAME, "active-final")
        status = state_element[-1].text
        states.append(status)
        print(f"Guía {guide_number}: Estado - {status}")
    
        # Verificar si el estado es "Entregado"
        if status.lower() == "entregado":
            try:
                # Extraer la fecha de entrega
                datetime_element = driver.find_element(By.XPATH, '//*[@id="ProgressContent"]/div/div/div[2]/div/div/table/tbody[1]/tr/td[1]/b/p/span')
                datetime_text = datetime_element.text
                delivery_dates.append(datetime_text)
                print(f"Tiempo: {datetime_text}")
            except Exception as e:
                print(f"No se pudo extraer la fecha y hora para la guía {guide_number}: {e}")
                delivery_dates.append(None)
        else:
            # Si el estado no es "Entregado", asignar "No Entregado" a delivery_dates
            delivery_dates.append("No Entregado")
    
        # Intentar extraer información de incidencias independientemente del estado
        try:
            incidence_arrow = WebDriverWait(driver, 4).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="IncidenceArrow"]')))
            incidence_arrow.click()
    
            incidents_date_element = driver.find_element(By.XPATH, '//*[@id="IncidenceContent"]/table/tbody/tr[2]/td[1]/b')
            incidents_date_text = incidents_date_element.get_attribute("textContent")
            incidents_date.append(incidents_date_text)
    
            incidents_desc_element = driver.find_element(By.XPATH, '/html/body/div/section/div/div[3]/div/div[5]/div[4]/div[2]/table/tbody/tr[2]/td[2]/p')
            incidents_desc_text = incidents_desc_element.get_attribute("textContent")
            incidents_desc.append(incidents_desc_text)
    
            print(f"Incidencia: {incidents_desc_text} - Fecha: {incidents_date_text}")
    
        except Exception as e:
            print(f"No se pudo extraer la incidencia para la guía {guide_number}: {e}")
            incidents_desc.append(None)
            incidents_date.append(None)
    
    except Exception as e:
        print(f"No se pudo encontrar el estado para la guía {guide_number}: {e}")
        states.append(None)
        delivery_dates.append("No Entregado")
        incidents_desc.append(None)
        incidents_date.append(None)
    # Realizar scraping para cada número de guía
def conversion(fecha_entrega):
    if fecha_entrega == "No Entregado":
        return fecha_entrega
    else:
        return pd.to_datetime(fecha_entrega, format='%d/%m/%Y %H:%M')


def process_file():
    st.title("Excel File Processor")
    # Upload file
    uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx", "xls"])

    if uploaded_file:
      # Read the uploaded file
        try:
            df = pd.read_excel(uploaded_file)

            # Display the uploaded file
            st.write("Uploaded File Preview:")
            st.dataframe(df)
            progress_bar = st.progress(0)
            progress_text = st.empty()
            total_guides = len(df)
            states.clear()
            delivery_dates.clear()
            incidents_desc.clear()
            incidents_date.clear()


            # Example processing: Add a new column
            for index,guide in enumerate(df['Numero de Guía Deprisa']):
                scrape_status(guide)
                
                progress_bar.progress((index + 1) / total_guides)
                progress_text.text(f"Processing guide {index + 1} of {total_guides}")
            driver.quit()
            df["Estado"] = states
            df["Fecha de entrega"] = delivery_dates
            df["Fechas de Incidentes"] = incidents_date
            df["Descripción de Incidente"]=incidents_desc
            # Display processed data
            st.write("Processed File Preview:")
            

            # Download the modified file
            # Aplicar la función de conversión a "Fecha de Entrega"
            df['Fecha de entrega'] = df['Fecha de entrega'].apply(conversion)
            df['Fecha de Creación'] = pd.to_datetime(df['Fecha de Creación'], format='%Y-%m-%d')
            df['Diferencia de días'] = df.apply(
                lambda row:( (datetime.now() - row['Fecha de Creación']).days 
                    if row['Fecha de entrega'] == "No Entregado" 
                    else (row['Fecha de entrega'] - row['Fecha de Creación']).days), 
                    axis=1
            )
            st.dataframe(df)
            #df1.to_excel('BD_LenaResultado.xlsx', index=False, engine='openpyxl')
            # Convert to Excel
            processed_file = convert_df_to_excel(df)

            st.download_button(
                label="Download Processed Excel File",
                data=processed_file,
                file_name="processed_file.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"Error processing file: {e}")

@st.cache_data
def convert_df_to_excel(dataframe):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        dataframe.to_excel(writer,index=False,)
    return output.getvalue()

if __name__ == "__main__":
    process_file()
