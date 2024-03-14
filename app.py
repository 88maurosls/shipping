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
    adjusted_rows = unique_costs_rows.copy()
    for index, row in adjusted_rows.iterrows():
        nazione = row[' NAZIONE']
        if nazione in countrycode_dict:
            iva = countrycode_dict[nazione]
            costo_spedizione = row[' COSTI_SPEDIZIONE']
            costo_senza_iva = costo_spedizione - (costo_spedizione * iva / 100)
            adjusted_rows.at[index, ' PREZZO_1'] = costo_senza_iva

    adjusted_rows[' COD_ART'] = "SHIPPING"
    adjusted_rows[' COD_ART_DOC'] = "SHIPPING"
    adjusted_rows[' DESCR_ART'] = "Shipping Costs"
    adjusted_rows[' DESCR_ART_ESTESA'] = "Shipping Costs"
    adjusted_rows[' DESCRIZIONE_RIGA'] = "Shipping Costs"
    adjusted_rows[' PROGRESSIVO_RIGA'] = adjusted_rows[' PROGRESSIVO_RIGA'].astype(str) + "-2"
    adjusted_rows[' HSCODE'] = ""  # Lascia vuota la colonna HSCODE

    # Preparare le righe dell'IVA
    vat_rows = pd.DataFrame()
    for index, row in unique_costs_rows.iterrows():
        nazione = row[' NAZIONE']
        if nazione in countrycode_dict:
            # Il calcolo dell'IVA avviene solo per i paesi nel countrycode.txt
            iva = countrycode_dict[nazione]
            # Calcolare il totale prezzo prodotti + costo spedizione per ogni NUM_DOC
            total_price = df[df[' NUM_DOC'] == row[' NUM_DOC']][' PREZZO_1'].sum()
            costo_spedizione = row[' COSTI_SPEDIZIONE']
            total_price += costo_spedizione
            costo_iva = (total_price * iva) / 100

            # Crea una nuova riga per l'IVA
            new_row = row.copy()
            new_row[' PREZZO_1'] = costo_iva
            new_row[' COD_ART'] = "VAT"
            new_row[' COD_ART_DOC'] = "VAT"
            new_row[' DESCR_ART'] = "VAT"
            new_row[' DESCR_ART_ESTESA'] = "VAT"
            new_row[' DESCRIZIONE_RIGA'] = "VAT"
            new_row[' PROGRESSIVO_RIGA'] = row[' PROGRESSIVO_RIGA'].astype(str) + "-3"
            new_row[' HSCODE'] = ""
            vat_rows = vat_rows.append(new_row, ignore_index=True)

    # Aggiungi sia le righe degli Shipping Costs che le righe dell'IVA al dataframe originale
    final_df = pd.concat([df, adjusted_rows, vat_rows], ignore_index=True)

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
