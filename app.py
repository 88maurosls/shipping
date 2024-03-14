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
        countrycode_df = pd.read_csv('countrycode.txt', delimiter=';', header=None, decimal=',')
        countrycode_dict = dict(zip(countrycode_df[0], countrycode_df[2]))
    except Exception as e:
        st.error(f"Errore nella lettura di countrycode.txt: {e}")
        countrycode_dict = {}

    # Identifica le righe con COSTI_SPEDIZIONE diversi da 0
    costs_rows = df[df[' COSTI_SPEDIZIONE'] != 0]

    # Filtra le righe uniche basate su NUM_DOC
    unique_costs_rows = costs_rows.drop_duplicates(subset=[' NUM_DOC'])

    # Initialize vat_rows as an empty DataFrame with the same columns as df
    vat_rows = pd.DataFrame(columns=df.columns)

    # Apporta le modifiche necessarie per le righe degli Shipping Costs
    for index, row in unique_costs_rows.iterrows():
        nazione = row[' NAZIONE']
        if nazione in countrycode_dict:
            iva = countrycode_dict[nazione]
            costo_spedizione = row[' COSTI_SPEDIZIONE']
            costo_senza_iva = costo_spedizione - (costo_spedizione * iva / 100)
            df.at[df.index[df[' NUM_DOC'] == row[' NUM_DOC']], ' PREZZO_1'] -= (costo_spedizione * iva / 100)
            
            # Prepare the VAT row if the country is in the countrycode dictionary
            vat_row = row.copy()
            vat_row[' PREZZO_1'] = costo_spedizione * iva / 100
            vat_row[' COD_ART'] = "VAT"
            vat_row[' COD_ART_DOC'] = "VAT"
            vat_row[' DESCR_ART'] = "VAT"
            vat_row[' DESCR_ART_ESTESA'] = "VAT"
            vat_row[' DESCRIZIONE_RIGA'] = "VAT"
            vat_row[' PROGRESSIVO_RIGA'] = row[' PROGRESSIVO_RIGA'] + "-3"
            vat_row[' HSCODE'] = ""
            vat_rows = vat_rows.append(vat_row, ignore_index=True)

    # Add Shipping Costs and VAT rows to the original dataframe
    final_df = pd.concat([df, vat_rows], ignore_index=True)

    # Sort the final dataframe by NUM_DOC and PROGRESSIVO_RIGA
    final_df.sort_values(by=[' NUM_DOC', ' PROGRESSIVO_RIGA'], inplace=True)

    # Convert the final dataframe to CSV, maintaining the original number format
    csv = final_df.to_csv(sep=';', index=False, float_format='%.2f', decimal=',')

    # Button to download the modified file
    st.download_button(
        label="Scarica il CSV modificato",
        data=io.BytesIO(csv.encode('utf-8')),
        file_name='modified_CLIARTFATT.csv',
        mime='text/csv',
    )

    st.balloons()
