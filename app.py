import streamlit as st
import pandas as pd
import io

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
        if nazione in countrycode_dict:
            iva = countrycode_dict[nazione]
            costo_spedizione = row[' COSTI_SPEDIZIONE']
            costo_senza_iva = costo_spedizione - (costo_spedizione * iva / 100)
            formatted_price = int(costo_senza_iva) if costo_senza_iva == int(costo_senza_iva) else costo_senza_iva
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

    # Calcola il valore della riga VAT
    for index, shipping_row in adjusted_rows.iterrows():
        num_doc = shipping_row[' NUM_DOC']
        same_doc_rows = df[(df[' NUM_DOC'] == num_doc) & (df[' PROGRESSIVO_RIGA'].astype(str).str.endswith("-2"))]
        total_shipping_cost = same_doc_rows[' PREZZO_1'].sum()
        
        if num_doc in countrycode_dict:
            iva = countrycode_dict[num_doc]
            # Calcola l'IVA sul totale dei costi di spedizione
            iva_amount = total_shipping_cost * iva / 100
            formatted_iva_amount = int(iva_amount) if iva_amount == int(iva_amount) else iva_amount
            # Aggiorna il valore della riga VAT
            vat_row_index = df[(df['NUM_DOC'] == num_doc) & (df['PROGRESSIVO_RIGA'].astype(str).str.endswith("-3"))].index[0]
            df.at[vat_row_index, ' PREZZO_1'] = formatted_iva_amount
        else:
            # Se il paese non è nel dizionario, impostare l'IVA a zero
            vat_row_index = df[(df['NUM_DOC'] == num_doc) & (df['PROGRESSIVO_RIGA'].astype(str).str.endswith("-3"))].index[0]
            df.at[vat_row_index, ' PREZZO_1'] = 0

    # Aggiungi sia le righe degli Shipping Costs che le righe dell'IVA al dataframe originale
    final_df = pd.concat([df, adjusted_rows], ignore_index=True)

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
        key="download_button_unique"  # Specifica una chiave univoca per il widget di download
    )
    st.balloons()
