import streamlit as st
import pandas as pd
import io

# Titolo dell'applicazione Streamlit
st.title('Modifica File CSV per Costi di Spedizione e IVA')

# Caricamento del file tramite drag-and-drop
uploaded_file = st.file_uploader("Carica il file CSV", type='csv')

if uploaded_file is not None:
    # Lettura del file caricato convertendo le virgole in punti nei numeri
    df = pd.read_csv(uploaded_file, delimiter=';', decimal=',')

    # Leggi il file countrycode.txt e crea un dizionario
    try:
        countrycode_df = pd.read_csv('countrycode.txt', delimiter=';', header=None, decimal=',')
        countrycode_dict = dict(zip(countrycode_df[0], countrycode_df[2]))
    except Exception as e:
        st.error(f"Errore nella lettura di countrycode.txt: {e}")
        countrycode_dict = {}

    # Identifica le righe con COSTI_SPEDIZIONE diversi da 0 e filtra le righe uniche basate su NUM_DOC
    costs_rows = df[df[' COSTI_SPEDIZIONE'] != 0].drop_duplicates(subset=[' NUM_DOC'])

    # Initialize adjusted_rows and vat_rows as empty DataFrames with the same columns as df
    adjusted_rows = pd.DataFrame(columns=df.columns)
    vat_rows = pd.DataFrame(columns=df.columns)

    # Process unique_costs_rows for Shipping and VAT rows
    for index, row in costs_rows.iterrows():
        nazione = row[' NAZIONE']
        costo_spedizione = row[' COSTI_SPEDIZIONE']
        if nazione in countrycode_dict:
            # Calculate VAT and Shipping Costs
            iva = countrycode_dict[nazione]
            costo_senza_iva = costo_spedizione - (costo_spedizione * iva / 100)
            costo_iva = (costo_spedizione * iva / 100)
            # Append Shipping Costs row
            ship_row = row.copy()
            ship_row[' PREZZO_1'] = costo_senza_iva
            ship_row[' COD_ART'] = "SHIPPINGCOSTS"
            ship_row[' COD_ART_DOC'] = "SHIPPINGCOSTS"
            ship_row[' DESCR_ART'] = "Shipping Costs"
            ship_row[' DESCR_ART_ESTESA'] = "Shipping Costs"
            ship_row[' DESCRIZIONE_RIGA'] = "Shipping Costs"
            ship_row[' PROGRESSIVO_RIGA'] = str(row[' PROGRESSIVO_RIGA']) + "-2"
            ship_row[' HSCODE'] = ""
            adjusted_rows = adjusted_rows.append(ship_row, ignore_index=True)
            
            # Append VAT row
            vat_row = row.copy()
            vat_row[' PREZZO_1'] = costo_iva
            vat_row[' COD_ART'] = "VAT"
            vat_row[' COD_ART_DOC'] = "VAT"
            vat_row[' DESCR_ART'] = "VAT"
            vat_row[' DESCR_ART_ESTESA'] = "VAT"
            vat_row[' DESCRIZIONE_RIGA'] = "VAT"
            vat_row[' PROGRESSIVO_RIGA'] = str(row[' PROGRESSIVO_RIGA']) + "-3"
            vat_row[' HSCODE'] = ""
            vat_rows = vat_rows.append(vat_row, ignore_index=True)
    
    # Combine all DataFrames
    final_df = pd.concat([df, adjusted_rows, vat_rows], ignore_index=True)

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
