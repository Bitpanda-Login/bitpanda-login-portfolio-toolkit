import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="BitpandaTax - Generador de Informe Fiscal España")
    parser.add_argument('--csv', help="Ruta al archivo CSV de Bitpanda")
    parser.add_argument('--year', help="Año fiscal a calcular")
    parser.add_argument('--fifo-prev', help="Ruta al archivo JSON de estado FIFO del año anterior")
    parser.add_argument('--output', help="Ruta de salida del PDF generado")
    parser.add_argument('--end-date', type=str, help='Fecha límite opcional (ej: 2024-03-31T23:59:59Z)')
    parser.add_argument('--fifo-start-date', type=str, help='Fecha de inicio del historial FIFO para compatibilidad con Blockpit (ej: 2022-01-01). Ignora compras anteriores a esta fecha.')
    
    args = parser.parse_args()
    
    if args.csv and args.year:
        # CLI Mode
        from core.calculator import calculate_taxes
        from pdf.generator import generate_pdf
        
        print(f"Calculando impuestos para el año {args.year}...")
        fifo_start = getattr(args, 'fifo_start_date', None)
        if fifo_start:
            print(f"Modo Blockpit: ignorando compras anteriores a {fifo_start}")
        metadata, results, fifo = calculate_taxes(args.csv, args.year, args.fifo_prev, args.end_date, fifo_start)
        
        output_path = args.output if args.output else f"informe_fiscal_{args.year}.pdf"
        print("Generando informe PDF...")
        generate_pdf(output_path, metadata, results, args.year)
        
        fifo_out_path = f"fifo_state_{args.year}.json"
        fifo.save_state(fifo_out_path)
        print(f"¡Hecho! Informe guardado en: {output_path}")
        print(f"Estado FIFO guardado en: {fifo_out_path}")
        
        if results.get('warnings'):
            print("\nAdvertencias:")
            for w in results['warnings']:
                print(f"- {w}")
    else:
        # GUI Mode
        from gui.main_window import run_gui
        run_gui()

if __name__ == "__main__":
    main()
