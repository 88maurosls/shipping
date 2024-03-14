import streamlit as st
import pandas as pd
import io

# Funzione per calcolare il prezzo senza IVA
def calculate_price_without_vat(costo_spedizione, iva):
    return costo_spedizione - (costo_spedizione * iva / 100)

# Funzione per calcolare l'IVA
def calculate_vat(costo_spedizione, iva):
    return costo_spedizione * iva / 100

# Titolo dell'applicazione Streamlit
st.title('Modifica File CSV per Costi di Spedizione e IVA')

# Caricamento del file tramite drag-and-drop
uploaded_file = st.file_uploader("Carica il file CSV", type='csv')

if uploaded_file is not None:
    # Lettura del file caricato
    df = pd.read_csv(uploaded_file, delimiter=';')

    # Leggi il file countrycode.txt e crea un dizionario
    try:
        countrycode_df = pd.read_csv('countrycode.txt', delimiter=';', header=None)
        countrycode_dict = dict(zip(countrycode_df[0], countrycode_df[2]))
    except Exception as e:
        st.error(f"Errore nella lettura di countrycode.txt: {e}")
        countrycode_dict = {}

    # Identifica le righe con COSTI_SPEDIZIONE diversi da 0
    costs_rows = df[df[' COSTI_SPEDIZIONE'] != 0]

    # Filtra le righe uniche basate su NUM_DOC
    unique_costs_rows = costs_rows.drop_duplicates(subset=[' NUM_DOC'])

    # Apporta le modifiche necessarie per le righe degli Shipping Costs
    adjusted_rows = unique_costs_rows.copy()
    for index, row in adjusted_rows.iterrows():
        nazione = row[' NAZIONE']
        add_vat_row = nazione in countrycode_dict
        if add_vat_row:
            iva = countrycode_dict[nazione]
            costo_spedizione = row[' COSTI_SPEDIZIONE']
            prezzo_senza_iva = calculate_price_without_vat(costo_spedizione, iva)
            formatted_price = int(prezzo_senza_iva) if prezzo_senza_iva == int(prezzo_senza_iva) else prezzo_senza_iva
            adjusted_rows.at[index, ' PREZZO_1'] = formatted_price
        else:
            # Se la nazione non è nel dizionario, mantenere il valore originale di COSTI_SPEDIZIONE
            adjusted_rows.at[index, ' PREZZO_1'] = row[' COSTI_SPEDIZIONE']

    adjusted_rows[' COD_ART'] = adjusted_rows[' COSTI_SPEDIZIONE'].apply(lambda x: f"SHIPPINGCOSTS{x}")
    adjusted_rows[' COD_ART_DOC'] = adjusted_rows[' COD_ART']
    adjusted_rows[' DESCR_ART'] = "Shipping Costs"
    adjusted_rows[' DESCR_ART_ESTESA'] = "Shipping Costs"
    adjusted_rows[' DESCRIZIONE_RIGA'] = "Shipping Costs"
    adjusted_rows[' PROGRESSIVO_RIGA'] = adjusted_rows[' PROGRESSIVO_RIGA'].astype(str) + "-2"
    adjusted_rows[' HSCODE'] = ""  # Lascia vuota la colonna HSCODE

# Crea una seconda riga aggiuntiva per l'IVA
vat_rows = unique_costs_rows.copy()
for index, row in vat_rows.iterrows():
    if add_vat_row:
        costo_spedizione = row[' COSTI_SPEDIZIONE']
        iva = countrycode_dict[row[' NAZIONE']]
        iva_amount = calculate_vat(costo_spedizione, iva)
        formatted_vat = int(iva_amount) if iva_amount == int(iva_amount) else iva_amount
        vat_rows.at[index, ' PREZZO_1'] = formatted_vat
    else:
        # Se la nazione non è nel dizionario, imposta a 0 l'IVA
        vat_rows.at[index, ' PREZZO_1'] = 0

vat_rows[' COD_ART'] = "VAT"
vat_rows[' COD_ART_DOC'] = vat_rows[' COD_ART']
vat_rows[' DESCR_ART'] = "VAT"
vat_rows[' DESCR_ART_ESTESA'] = "VAT"
vat_rows[' DESCRIZIONE_RIGA'] = "VAT"
vat_rows[' PROGRESSIVO_RIGA'] = vat_rows[' PROGRESSIVO_RIGA'].astype(str) + "-3"
vat_rows[' HSCODE'] = ""  # Lascia vuota la colonna HSCODE

# Aggiungi sia le righe degli Shipping Costs che le righe dell'IVA al dataframe originale
final_df = pd.concat([df, adjusted_rows, vat_rows], ignore_index=True)

# Ordina il dataframe finale per NUM_DOC
final_df.sort_values(by=[' NUM_DOC'], inplace=True)

# Converti il dataframe finale in CSV
csv = final_df.to_csv(sep=';', index=False, float_format='%.2f').encode('utf-8').decode('utf-8').replace('.', ',').encode('utf-8')

# Bottone per il download del file modificato
st.download_button(
    label="Scarica il CSV modificato",
    data=io.BytesIO(csv),
    file_name='modified_CLIARTFATT.csv',
    mime='text/csv',
)
st.balloons()
