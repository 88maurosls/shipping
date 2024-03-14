import streamlit as st
import pandas as pd
import io

# Titolo dell'applicazione Streamlit
st.title('Modifica File CSV per Costi di Spedizione e IVA')

# Caricamento del file tramite drag-and-drop
uploaded_file = st.file_uploader("Carica il file CSV", type='csv')

if uploaded_file is not None:
    # Lettura del file caricato
    df = pd.read_csv(uploaded_file, delimiter=';', decimal=',')

    # Leggi il file countrycode.txt e crea un dizionario
    try:
        countrycode_df = pd.read_csv('countrycode.txt', delimiter=';', header=None)
        countrycode_dict = dict(zip(countrycode_df[0], countrycode_df[2]))
    except Exception as e:
        st.error(f"Errore nella lettura di countrycode.txt: {e}")
        countrycode_dict = {}

    # Identifica le righe con COSTI_SPEDIZIONE diversi da 0
    shipping_rows = df[df[' COSTI_SPEDIZIONE'] != 0]

    # Identifica le righe con NAZIONE presente in countrycode_dict
    vat_rows = df[df[' NAZIONE'].isin(countrycode_dict)]

    # Modifica le righe degli Shipping Costs
for index, row in shipping_rows.iterrows():
    nazione = row[' NAZIONE']
    if nazione in countrycode_dict:
        iva = countrycode_dict[nazione]
        costo_spedizione = row[' COSTI_SPEDIZIONE']
        costo_senza_iva = costo_spedizione - (costo_spedizione * iva / 100)
        formatted_price = int(costo_senza_iva) if costo_senza_iva == int(costo_senza_iva) else costo_senza_iva
        df.loc[index, ' PREZZO_1'] = formatted_price
    else:
        df.loc[index, ' PREZZO_1'] = row[' COSTI_SPEDIZIONE']
    df.loc[index, ' COD_ART'] = f"SHIPPINGCOSTS{index}"
    df.loc[index, ' DESCR_ART'] = "Shipping Costs"
    df.loc[index, ' DESCR_ART_ESTESA'] = "Shipping Costs"
    df.loc[index, ' DESCRIZIONE_RIGA'] = "Shipping Costs"
    df.loc[index, ' PROGRESSIVO_RIGA'] = df.loc[index, ' PROGRESSIVO_RIGA'] + "-2"
    df.loc[index, ' HSCODE'] = ""

# Modifica le righe del VAT
for index, row in vat_rows.iterrows():
    iva = countrycode_dict[row[' NAZIONE']]
    costo_spedizione = row[' PREZZO_1']
    costo_iva = costo_spedizione * iva / 100
    formatted_vat = int(costo_iva) if costo_iva == int(costo_iva) else costo_iva
    df.loc[index, ' PREZZO_1'] = formatted_vat
    df.loc[index, ' COD_ART'] = "VAT"
    df.loc[index, ' DESCR_ART'] = "VAT"
    df.loc[index, ' DESCR_ART_ESTESA'] = "VAT"
    df.loc[index, ' DESCRIZIONE_RIGA'] = "VAT"
    df.loc[index, ' PROGRESSIVO_RIGA'] = df.loc[index, ' PROGRESSIVO_RIGA'] + "-3"
    df.loc[index, ' HSCODE'] = ""


    # Combina le righe degli Shipping Costs e del VAT con il DataFrame originale
    final_df = pd.concat([df, shipping_rows, vat_rows], ignore_index=True)

    # Ordina il DataFrame finale per NUM_DOC
    final_df.sort_values(by=[' NUM_DOC'], inplace=True)

    # Converti il DataFrame finale in CSV
    csv = final_df.to_csv(sep=';', index=False, float_format='%.2f').encode('utf-8').decode('utf-8').replace('.', ',').encode('utf-8')

    # Bottone per il download del file modificato
    st.download_button(
        label="Scarica il CSV modificato",
        data=io.BytesIO(csv),
        file_name='modified_CLIARTFATT.csv',
        mime='text/csv',
    )
    st.balloons()
