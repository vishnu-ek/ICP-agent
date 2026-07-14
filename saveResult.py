import pandas as pd
import datetime
from openpyxl.utils import get_column_letter

dt = str(datetime.datetime.now().replace(microsecond=0).strftime("%Y-%m-%d_%H-%M-%S"))
def exportToExcel(memory, filename=f"icp_memory_export_{dt}.xlsx"):
    data = []
    
    for fit in memory.allFits:
        speakers = ", ".join(f"{name} ({role})" for name, role in fit.speakers)
        
        # Filter down actions
        lookups = [act for act in fit.itsActionRecord if act.lookupQuery or act.gatheredContext]
        
        # Extract queries and contexts
        queries = [f"Yes (Query: {act.lookupQuery})" if act.lookupQuery else "Yes" for act in lookups]
        contexts = [act.gatheredContext for act in lookups if act.gatheredContext]
        
        data.append({
            "Memory Goal": memory.goal,
            "PDF Path": memory.pdfPath,
            "Company": fit.company,
            "Speakers": speakers,
            "Fit Score": fit.fitScore,
            "Reasoning": fit.reasoning,
            "Lookup Done?": "\n".join(queries) if queries else "No",
            "Gathered Context": "\n\n---\n\n".join(contexts) if contexts else "N/A"
        })
        
    df = pd.DataFrame(data)
    
    # Save to Excel
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='ICP Fits')
        sheet = writer.sheets['ICP Fits']
        
        for idx, col_name in enumerate(df.columns, start=1):
            col_letter = get_column_letter(idx)
            
            # Auto-size
            max_len = max(df[col_name].astype(str).map(len).max(), len(col_name))
            sheet.column_dimensions[col_letter].width = min(max_len + 2, 60)
            
            # Wrap text
            for cell in sheet[col_letter]:
                cell.alignment = cell.alignment.copy(wrapText=True, vertical='top')

    print(f"Data saved to {filename}")
