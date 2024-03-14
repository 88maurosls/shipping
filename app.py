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

    # Apporta le modifiche necessarie per le righe degli Shipping Costs
    # e prepara le righe IVA se la NAZIONE è nel dizionario
    vat_rows = pd.DataFrame()
    for index, row in unique_costs_rows.iterrows():
        nazione = row[' NAZIONE']
        costo_spedizione = row[' COSTI_SPEDIZIONE']
        if nazione in countrycode_dict:
            iva = countrycode_dict[nazione]
            costo_senza_iva = costo_spedizione - (costo_spedizione * iva / 100)
            # Aggiorna il costo spedizione escludendo l'IVA
            unique_costs_rows.at[index, ' PREZZO_1'] = costo_senza_iva
            
            # Calcola l'IVA sulla somma di costo dell'articolo e costo spedizione
            total_price = df[df[' NUM_DOC'] == row[' NUM_DOC']][' PREZZO_1'].sum()
            total_price += costo_spedizione
            costo_iva = (total_price * iva) / 100
            
            # Crea la nuova riga VAT
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

    unique_costs_rows[' COD_ART'] = unique_costs_rows[' COSTI_SPEDIZIONE'].apply(lambda x: f"SHIPPINGCOSTS{x}")
    unique_costs_rows[' COD_ART_DOC'] = unique_costs_rows[' COD_ART']
    unique_costs_rows[' DESCR_ART'] = "Shipping Costs"
    unique_costs_rows[' DESCR_ART_ESTESA'] = "Shipping Costs"
    unique_costs_rows[' DESCRIZIONE_RIGA'] = "Shipping Costs"
    unique_costs_rows[' PROGRESSIVO_RIGA'] = unique_costs_rows[' PROGRESSIVO_RIGA'].astype(str) + "-2"
    unique_costs_rows[' HSCODE'] = ""  # Lascia vuota la colonna HSCODE

    # Aggiungi le righe degli Shipping Costs e le righe dell'IVA (se applicabile) al dataframe originale
    final_df = pd.concat([df, unique_costs_rows, vat_rows], ignore_index=True)

    # Ordina il dataframe finale per NUM_DOC e PROGRESSIVO_RIGA
    final_df.sort_values(by=[' NUM_DOC', ' PROGRESSIVO_RIGA'], inplace=True)

    # Converti il dataframe finale in CSV mantenendo il formato originale per i numeri
    csv = final_df.to_csv(sep=';', index=False, float_format='%.2f', decimal=',')

    # Bottone per il download del file modificato
    st.download_button(
        label="Scarica il CSV modificato",
        data=io.BytesIO(csv.encode('utf-8')),
        file_name='modified_CLIARTFATT.csv',
        mime='text/csv',
    )

    st.balloons()
