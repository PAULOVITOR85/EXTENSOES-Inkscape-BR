Extensão: Contorno e Preenchimento não-destrutiva
Essa extenssão foi feito com claude code.

📦 Extensão: Contorno e Preenchimento Avançado
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

Salve ambos os arquivos (contorno_preenchimento.py e contorno_preenchimento.inx) na mesma pasta. Reinicie o Inkscape. A extensão aparecerá em:
Efeitos → Estilo Visual → Contorno e Preenchimento Avançado…

⚠️ Notas de uso

Ctrl+Z desfaz completamente (o grupo wrapper some e o original é restaurado)
Rodar a extensão duas vezes em sequência cria grupos aninhados — use Ctrl+Z entre aplicações
O atributo interpreter="python" na tag <command> garante funcionamento no Windows e Linux
Compatível com paths, retângulos, elipses, texto e grupos SVG


==================================================================================



This extension was made with claude code.

📦 Extension: Advanced Contour and Fill
Non-destructive architecture
Each selected object is wrapped in a <g id="cpe-…"> and the effects are separate layers in the following stacking order (bottom → top):

[0] clone-external-brightness ← feColorMatrix + feGaussianBlur
[1] clone-contorno ← fill:none, just stroke (or gradient)
[2] ORIGINAL ← untouched (except fill, if gradient active)
[3] clone-inner-glow ← feFlood → clip → blur → clip

🎛️ Interface — 4 Tabs with 24 parameters
TabControls✏ OutlineWidth (0.1–200px), Opacity, Solid color, Linear gradient with angle (0–360°)✨ OuterGlowColor, Blur (0–100), Expansion (spread), Opacity💫InnerGlowColor, Blur (0–100), Opacity🎨FillType (linear/radial), Angle, Color1+opacity, Color2+opacity

📁 Where to save the files:

Linux/macOS: ~/.config/inkscape/extensions/

Windows: %APPDATA%\inkscape\extensions\

To confirm the exact path: Edit → Preferences → System → User Extensions

Save both files (contorno_preenchimento.py and contour_preenchimento.inx) in the same folder. Restart Inkscape. The extension will appear in:
Effects → Visual Style → Advanced Outline and Fill…

⚠️ Usage notes

Ctrl+Z completely undoes it (the wrapper group disappears and the original is restored)
Running the extension twice in sequence creates nested groups — use Ctrl+Z between applications
The interpreter="python" attribute in the <command> tag guarantees operation on Windows and Linux
Supports paths, rectangles, ellipses, text and SVG groups
