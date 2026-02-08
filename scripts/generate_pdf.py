"""
Convert Markdown Report to PDF for Hackathon Submission
Uses markdown2 to convert to HTML, then opens for printing as PDF
"""
import markdown2
import os
from pathlib import Path

def convert_report():
    # Read the markdown file
    report_path = Path(__file__).parent.parent / "report" / "Prometheus_Siren_Complete_Report.md"
    output_html = Path(__file__).parent.parent / "report" / "Prometheus_Siren_Report.html"
    
    with open(report_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Convert to HTML with extras
    html_content = markdown2.markdown(
        md_content,
        extras=['tables', 'fenced-code-blocks', 'header-ids', 'toc']
    )
    
    # Create styled HTML
    styled_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Prometheus-Siren: A Self-Evolving Cyber-Immune System</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px;
            color: #333;
        }}
        h1 {{ color: #e74c3c; border-bottom: 3px solid #e74c3c; padding-bottom: 10px; }}
        h2 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 8px; margin-top: 40px; }}
        h3 {{ color: #34495e; }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Consolas', monospace;
        }}
        pre {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        pre code {{
            background: none;
            color: inherit;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background: #3498db;
            color: white;
        }}
        tr:nth-child(even) {{
            background: #f9f9f9;
        }}
        blockquote {{
            border-left: 4px solid #e74c3c;
            margin: 20px 0;
            padding: 10px 20px;
            background: #ffeaa7;
        }}
        .mermaid-placeholder {{
            background: #ecf0f1;
            border: 2px dashed #95a5a6;
            padding: 20px;
            text-align: center;
            margin: 20px 0;
            color: #7f8c8d;
        }}
        @media print {{
            body {{ padding: 20px; }}
            pre {{ white-space: pre-wrap; }}
        }}
    </style>
</head>
<body>
{html_content}
<hr>
<p style="text-align: center; color: #7f8c8d;">
    <em>Prometheus-Siren Team | Convolve 4.0 - Pan-IIT AI/ML Hackathon | January 2026</em>
</p>
</body>
</html>"""
    
    # Write HTML file
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(styled_html)
    
    print(f"✅ HTML report created: {output_html}")
    print(f"")
    print(f"📄 TO CREATE PDF:")
    print(f"   1. Open the HTML file in Chrome/Edge")
    print(f"   2. Press Ctrl+P (Print)")
    print(f"   3. Select 'Save as PDF' as destination")
    print(f"   4. Save as 'Prometheus_Siren_Report.pdf'")
    print(f"")
    print(f"🔗 Then upload to Google Drive and share with 'Anyone with link'")
    
    # Try to open in browser
    import webbrowser
    webbrowser.open(str(output_html))

if __name__ == "__main__":
    convert_report()
