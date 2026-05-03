Extensão: Contorno e Preenchimento não-destrutiva
Essa extenssão foi feito com claude code.

📦 Extensão: Estilo visual
Arquitetura não-destrutiva
Cada objeto selecionado é envolvido num <g id="cpe-…"> e os efeitos são camadas separadas na seguinte ordem de empilhamento (baixo → cima):

[0] clone-brilho-externo  ← feColorMatrix + feGaussianBlur
[1] clone-contorno        ← fill:none, só stroke (ou gradiente)
[2] ORIGINAL              ← intocado (exceto fill, se gradiente ativo)
[3] clone-brilho-interno  ← feFlood → clip → blur → clip

🎛️ Interface — 4 Abas com 24 parâmetros
AbaControles✏ ContornoLargura (0.1–200px), Opacidade, Cor sólida, Gradiente linear com ângulo (0–360°)✨ Brilho ExternoCor, Desfoque (0–100), Expansão (spread), Opacidade💫 Brilho InternoCor, Desfoque (0–100), Opacidade🎨 PreenchimentoTipo (linear/radial), Ângulo, Cor1+opacidade, Cor2+opacidade

📁 Onde salvar os arquivos:

Linux / macOS:   ~/.config/inkscape/extensions/

Windows:   %APPDATA%\inkscape\extensions\

Para confirmar o caminho exacto: Editar → Preferências → Sistema → Extensões do usuário

Salve ambos os arquivos .py e .inx na pasta extensão do inkscape. Reinicie o programa. A extensão aparecerá em:
Efeitos → Estilo Visual → 
Como aparece no Inkscape:

Efeitos
 └── Estilo Visual
       ├── Contorno...                ← cpe_01_contorno.inx
       ├── Brilho Externo...          ← cpe_02_externo.inx
       ├── Brilho Interno...          ← cpe_03_interno.inx
       └── Gradiente de Preenchimento... ← cpe_04_fill.inx

⚠️ Notas de uso

Ctrl+Z desfaz completamente (o grupo wrapper some e o original é restaurado)
Rodar a extensão duas vezes em sequência cria grupos aninhados — use Ctrl+Z entre aplicações
O atributo interpreter="python" na tag <command> garante funcionamento no Windows e Linux
Compatível com paths, retângulos, elipses, texto e grupos SVG


==================================================================================



Extension: Non-destructive Contour and Fill
This extension was created using Claude Code.

📦 Extension: Visual Style
Non-destructive architecture
Each selected object is wrapped in a <g id="cpe-…"> and the effects are separate layers in the following stacking order (bottom → top):

[0] clone-outer-glow ← feColorMatrix + feGaussianBlur
[1] clone-outline ← fill:none, only stroke (or gradient)
[2] ORIGINAL ← untouched (except fill, if gradient active)
[3] clone-inner-glow ← feFlood → clip → blur → clip

🎛️ Interface — 4 Tabs with 24 parameters
Controls Tab ✏ OutlineWidth (0.1–200px), Opacity, Solid Color, Linear Gradient with angle (0–360°) ✨ Outer Glow Color, Blur (0–100), Spread, Opacity💫 Inner GlowColor, Blur (0–100), Opacity🎨 FillType (linear/radial), Angle, Color1+opacity, Color2+opacity

📁 Where to save the files:

Linux / macOS: ~/.config/inkscape/extensions/

Windows: %APPDATA%\inkscape\extensions\

To confirm the exact path: Edit → Preferences → System → User Extensions

Save both the .py and .inx files in the Inkscape extensions folder. Restart the program. The extension will appear in:
Effects → Visual Style →

How it appears in Inkscape:

Effects
└── Visual Style
├── Outline... ← cpe_01_contour.inx
├── Outer Glow... ← cpe_02_outer.inx
├── Inner Glow... ← cpe_03_inner.inx
└── Fill Gradient... ← cpe_04_fill.inx

⚠️ Usage Notes

Ctrl+Z completely undoes (the wrapper group disappears and the original is restored)
Running the extension twice in sequence creates nested groups — use Ctrl+Z between applications
The attribute interpreter="python" in the <command> tag ensures Works on Windows and Linux
Compatible with paths, rectangles, ellipses, text, and SVG groups
