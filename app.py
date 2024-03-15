import streamlit as st
import pandas as pd
import io

# Funzione per l'elaborazione delle righe delle spedizioni
def process_vat_rows(rows, countrycode_dict, df_original):
    vat_rows = rows.copy()
    vat_rows = vat_rows[vat_rows[' NAZIONE'].isin(countrycode_dict.keys())]

    for index, row in vat_rows.iterrows():
        num_doc = row[' NUM_DOC']
        iva = countrycode_dict.get(row[' NAZIONE'], 0)  # Ottieni il valore dell'IVA come numero

        # Assicurati che l'IVA sia un numero
        if not isinstance(iva, (int, float)):
            st.error(f"IVA non valida per la nazione {row[' NAZIONE']}: {iva}")
            continue

        # Calcola la somma di PREZZO_1 per ogni NUM_DOC unico
        unique_rows = df_original[(df_original[' NUM_DOC'] == num_doc)].drop_duplicates(subset=[' PROGRESSIVO_RIGA'])
        try:
            sum_prezzo = unique_rows[' PREZZO_1'].str.replace(",", ".").astype(float).sum()
        except Exception as e:
            st.error(f"Errore nella somma di PREZZO_1 per NUM_DOC {num_doc}: {e}")
            continue

        costo_iva = sum_prezzo * iva / 100
        formatted_vat = int(costo_iva) if costo_iva == int(costo_iva) else costo_iva
        vat_rows.at[index, ' PREZZO_1'] = formatted_vat

# Funzione modificata per l'elaborazione delle righe dell'IVA
def process_vat_rows(rows, countrycode_dict, df_original):
    vat_rows = rows.copy()
    vat_rows = vat_rows[vat_rows[' NAZIONE'].isin(countrycode_dict.keys())]

    for index, row in vat_rows.iterrows():
        num_doc = row[' NUM_DOC']
        iva_str = countrycode_dict.get(row[' NAZIONE'], "0")
        try:
            iva = float(iva_str.replace(",", "."))  # Sostituisce la virgola con il punto se necessario
        except ValueError:
            st.error(f"Errore nella conversione dell'IVA per la nazione {row[' NAZIONE']}: {iva_str}")
            continue

        unique_rows = df_original[(df_original[' NUM_DOC'] == num_doc)].drop_duplicates(subset=[' PROGRESSIVO_RIGA'])
        try:
            sum_prezzo = unique_rows[' PREZZO_1'].str.replace(",", ".").astype(float).sum()
        except Exception as e:
            st.error(f"Errore nella somma di PREZZO_1 per NUM_DOC {num_doc}: {e}")
            continue

        costo_iva = sum_prezzo * iva / 100
        formatted_vat = int(costo_iva) if costo_iva == int(costo_iva) else costo_iva
        vat_rows.at[index, ' PREZZO_1'] = formatted_vat

    # Imposta i valori per le altre colonne
    vat_rows[' COD_ART'] = "VAT"
    vat_rows[' COD_ART_DOC'] = vat_rows[' COD_ART']
    vat_rows[' DESCR_ART'] = "VAT"
    vat_rows[' DESCR_ART_ESTESA'] = "VAT"
    vat_rows[' DESCRIZIONE_RIGA'] = "VAT"
    vat_rows[' PROGRESSIVO_RIGA'] = vat_rows[' PROGRESSIVO_RIGA'].astype(str) + "-3"
    vat_rows[' HSCODE'] = ""  # Lascia vuota la colonna HSCODE
    return vat_rows


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

    # Elabora le righe delle spedizioni
    adjusted_rows = process_shipping_rows(unique_costs_rows, countrycode_dict)

    # Elabora le righe dell'IVA
    vat_rows = process_vat_rows(unique_costs_rows, countrycode_dict)

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
