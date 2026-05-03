#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════╗
║  CPE — Contorno e Preenchimento Avançado  |  Engine Compartilhado ║
║  Inkscape 1.4+  |  GPL v2+  |  Linux · Windows · macOS           ║
╠═══════════════════════════════════════════════════════════════════╣
║  Este arquivo é chamado por QUATRO extensões .inx independentes:  ║
║    cpe_01_contorno.inx   →  modo "contorno"                       ║
║    cpe_02_externo.inx    →  modo "externo"                        ║
║    cpe_03_interno.inx    →  modo "interno"                        ║
║    cpe_04_fill.inx       →  modo "fill"                           ║
║                                                                   ║
║  O argumento --modo seleciona qual bloco de efeito executar.      ║
║  Cada .inx declara apenas os parâmetros do seu próprio efeito.    ║
╚═══════════════════════════════════════════════════════════════════╝

Arquitetura não-destrutiva:
  O objeto original nunca é deletado.  Os efeitos são camadas
  separadas dentro de um grupo wrapper <g id="cpe-…">.

  Ordem de empilhamento (baixo → cima):
    [0] clone-brilho-externo   feColorMatrix + feGaussianBlur
    [1] clone-contorno         fill:none, só stroke / gradiente
    [2] ORIGINAL               intocado (exceto fill no modo fill)
    [3] clone-brilho-interno   feFlood → clip → blur → clip
"""

import math
import copy
import inkex
from inkex import Group
from lxml import etree

# ──────────────────────────────────────────────────────────────────
SVG_NS = "http://www.w3.org/2000/svg"
INKNS  = "http://www.inkscape.org/namespaces/inkscape"


def _n(tag: str) -> str:
    """Retorna tag qualificada com namespace SVG."""
    return f'{{{SVG_NS}}}{tag}'


# ══════════════════════════════════════════════════════════════════
class CPEEngine(inkex.EffectExtension):
    """
    Engine único chamado pelos quatro .inx.
    O parâmetro --modo determina qual bloco lógico é executado.
    """

    # ──────────────────────────────────────────────────────────────
    # ARGUMENTOS — superconjunto de todos os quatro .inx
    # Cada .inx passa apenas o subconjunto que lhe pertence;
    # os demais ficam nos valores-padrão definidos aqui.
    # ──────────────────────────────────────────────────────────────
    def add_arguments(self, pars):

        # Roteador de modo — injetado por cada .inx como <param hidden>
        pars.add_argument("--modo", type=str, dest="modo",
                          default="contorno")

        # ── CONTORNO ──────────────────────────────────────────────
        pars.add_argument("--stroke_width", type=float,
                          dest="stroke_width", default=2.0)
        pars.add_argument("--stroke_opacity", type=float,
                          dest="stroke_opacity", default=1.0)
        pars.add_argument("--stroke_color", type=inkex.Color,
                          dest="stroke_color",
                          default=inkex.Color("#000000"))
        pars.add_argument("--stroke_gradient", type=inkex.Boolean,
                          dest="stroke_gradient", default=False)
        pars.add_argument("--stroke_grad_color1", type=inkex.Color,
                          dest="stroke_grad_color1",
                          default=inkex.Color("#ff0000"))
        pars.add_argument("--stroke_grad_color2", type=inkex.Color,
                          dest="stroke_grad_color2",
                          default=inkex.Color("#0000ff"))
        pars.add_argument("--stroke_grad_angle", type=float,
                          dest="stroke_grad_angle", default=0.0)

        # ── BRILHO EXTERNO ────────────────────────────────────────
        pars.add_argument("--outer_color", type=inkex.Color,
                          dest="outer_color",
                          default=inkex.Color("#ffff00"))
        pars.add_argument("--outer_blur", type=float,
                          dest="outer_blur", default=8.0)
        pars.add_argument("--outer_spread", type=float,
                          dest="outer_spread", default=0.0)
        pars.add_argument("--outer_opacity", type=float,
                          dest="outer_opacity", default=0.8)

        # ── BRILHO INTERNO ────────────────────────────────────────
        pars.add_argument("--inner_color", type=inkex.Color,
                          dest="inner_color",
                          default=inkex.Color("#00ffff"))
        pars.add_argument("--inner_blur", type=float,
                          dest="inner_blur", default=8.0)
        pars.add_argument("--inner_opacity", type=float,
                          dest="inner_opacity", default=0.8)

        # ── GRADIENTE DE PREENCHIMENTO ────────────────────────────
        pars.add_argument("--fill_gradient_type", type=str,
                          dest="fill_gradient_type", default="linear")
        pars.add_argument("--fill_angle", type=float,
                          dest="fill_angle", default=0.0)
        pars.add_argument("--fill_color1", type=inkex.Color,
                          dest="fill_color1",
                          default=inkex.Color("#ff6600"))
        pars.add_argument("--fill_opacity1", type=float,
                          dest="fill_opacity1", default=1.0)
        pars.add_argument("--fill_color2", type=inkex.Color,
                          dest="fill_color2",
                          default=inkex.Color("#ffff00"))
        pars.add_argument("--fill_opacity2", type=float,
                          dest="fill_opacity2", default=1.0)

    # ──────────────────────────────────────────────────────────────
    # MÉTODO PRINCIPAL — despacha para o modo correto
    # ──────────────────────────────────────────────────────────────
    def effect(self):
        if not self.svg.selection:
            inkex.errormsg(
                "⚠  Nenhum objeto selecionado!\n\n"
                "Selecione um ou mais objetos no canvas\n"
                "antes de aplicar esta extensão.\n\n"
                "Dica: use Ctrl+A para selecionar tudo."
            )
            return

        modo = self.options.modo.strip().lower()

        # Tabela de despacho: modo → método
        despacho = {
            "contorno": self._modo_contorno,
            "externo":  self._modo_externo,
            "interno":  self._modo_interno,
            "fill":     self._modo_fill,
        }

        if modo not in despacho:
            inkex.errormsg(f"Modo desconhecido: '{modo}'.\n"
                           f"Use: {', '.join(despacho)}")
            return

        executor = despacho[modo]
        for elem in list(self.svg.selection.values()):
            try:
                executor(elem)
            except Exception as err:
                inkex.errormsg(
                    f"Erro no elemento "
                    f"'{elem.get_id() or type(elem).__name__}':\n{err}"
                )

    # ══════════════════════════════════════════════════════════════
    # MODOS — cada um envolve o elemento num grupo e aplica 1 efeito
    # ══════════════════════════════════════════════════════════════

    def _modo_contorno(self, elem):
        """Aplica contorno (stroke) com cor sólida ou gradiente linear."""
        grupo = self._criar_grupo_wrapper(elem, rotulo="CPE: Contorno")
        self._aplicar_contorno(elem, grupo)

    def _modo_externo(self, elem):
        """Aplica brilho externo (outer glow) via filtro SVG."""
        grupo = self._criar_grupo_wrapper(elem, rotulo="CPE: Brilho Externo")
        self._aplicar_brilho_externo(elem, grupo)

    def _modo_interno(self, elem):
        """Aplica brilho interno (inner glow) via filtro SVG."""
        grupo = self._criar_grupo_wrapper(elem, rotulo="CPE: Brilho Interno")
        self._aplicar_brilho_interno(elem, grupo)

    def _modo_fill(self, elem):
        """Aplica gradiente de preenchimento (linear ou radial) ao fill."""
        # Fill não precisa de grupo wrapper — só altera o estilo do original
        self._aplicar_gradiente_preenchimento(elem)

    # ══════════════════════════════════════════════════════════════
    # INFRAESTRUTURA — grupo wrapper
    # ══════════════════════════════════════════════════════════════

    def _criar_grupo_wrapper(self, elem, rotulo: str) -> Group:
        """
        Substitui elem no DOM por um <g> contendo elem.
        Retorna o grupo para que os efeitos possam inserir camadas.
        """
        pai = elem.getparent()
        if pai is None:
            raise RuntimeError("Elemento sem pai no DOM — não pode ser agrupado.")

        grupo = Group()
        grupo.set('id', self.svg.get_unique_id('cpe-'))
        grupo.set(f'{{{INKNS}}}label', rotulo)
        grupo.set(f'{{{INKNS}}}groupmode', 'layer')

        idx = list(pai).index(elem)
        pai.insert(idx, grupo)
        pai.remove(elem)
        grupo.append(elem)    # original fica no grupo, intocado

        return grupo

    # ══════════════════════════════════════════════════════════════
    # EFEITO: CONTORNO
    # ══════════════════════════════════════════════════════════════

    def _aplicar_contorno(self, elem, grupo):
        """
        Clone do elemento com fill=none e stroke configurado.
        Inserido imediatamente abaixo do original no grupo.
        """
        opts  = self.options
        clone = copy.deepcopy(elem)
        clone.set('id', self.svg.get_unique_id('cpe-stroke-'))

        estilo = inkex.Style()
        estilo['fill']            = 'none'
        estilo['stroke-width']    = str(opts.stroke_width)
        estilo['stroke-opacity']  = str(max(0.0, min(1.0, opts.stroke_opacity)))
        estilo['stroke-linejoin'] = 'round'
        estilo['stroke-linecap']  = 'round'
        estilo['paint-order']     = 'stroke fill markers'

        if opts.stroke_gradient:
            gid = self._criar_gradiente_linear(
                cor1=opts.stroke_grad_color1,
                cor2=opts.stroke_grad_color2,
                angulo=opts.stroke_grad_angle,
                op1=1.0, op2=1.0,
                prefixo='cpe-sg-'
            )
            estilo['stroke'] = f'url(#{gid})'
        else:
            estilo['stroke'] = self._hex_rgb(opts.stroke_color)

        clone.set('style', str(estilo))

        # Insere antes do original → fica abaixo na renderização
        grupo.insert(list(grupo).index(elem), clone)

    # ══════════════════════════════════════════════════════════════
    # EFEITO: BRILHO EXTERNO
    # ══════════════════════════════════════════════════════════════

    def _aplicar_brilho_externo(self, elem, grupo):
        """
        Clone colorido com filtro de desfoque gaussiano.
        Inserido no índice 0 do grupo (mais abaixo de tudo).
        """
        opts = self.options
        fid  = self._criar_filtro_outer_glow(
            cor=opts.outer_color,
            blur=opts.outer_blur + opts.outer_spread,
            opacidade=opts.outer_opacity
        )

        clone = copy.deepcopy(elem)
        clone.set('id', self.svg.get_unique_id('cpe-og-'))

        estilo = inkex.Style()
        estilo['fill']   = self._hex_rgb(opts.outer_color)
        estilo['stroke'] = 'none'
        estilo['filter'] = f'url(#{fid})'

        clone.set('style', str(estilo))
        grupo.insert(0, clone)

    def _criar_filtro_outer_glow(self, cor, blur, opacidade) -> str:
        """
        Filtro SVG: feColorMatrix (coloriza) → feGaussianBlur (aura).
        Cria o elemento <filter> em <defs> e retorna seu id.
        """
        fid  = self.svg.get_unique_id('cpe-f-og-')
        filt = etree.SubElement(self.svg.defs, _n('filter'))
        filt.set('id', fid)
        filt.set('x', '-100%');  filt.set('width',  '300%')
        filt.set('y', '-100%');  filt.set('height', '300%')
        filt.set('color-interpolation-filters', 'sRGB')

        r = int(cor.red)   / 255.0
        g = int(cor.green) / 255.0
        b = int(cor.blue)  / 255.0

        cm = etree.SubElement(filt, _n('feColorMatrix'))
        cm.set('type', 'matrix');  cm.set('in', 'SourceGraphic')
        cm.set('values', (
            f'0 0 0 0 {r:.4f}  '
            f'0 0 0 0 {g:.4f}  '
            f'0 0 0 0 {b:.4f}  '
            f'0 0 0 {opacidade:.4f} 0'
        ))
        cm.set('result', 'colorized')

        gb = etree.SubElement(filt, _n('feGaussianBlur'))
        gb.set('in', 'colorized')
        gb.set('stdDeviation', f'{max(0.1, blur):.2f}')

        return fid

    # ══════════════════════════════════════════════════════════════
    # EFEITO: BRILHO INTERNO
    # ══════════════════════════════════════════════════════════════

    def _aplicar_brilho_interno(self, elem, grupo):
        """
        Clone com filtro de brilho interno, inserido após o original.
        """
        opts = self.options
        fid  = self._criar_filtro_inner_glow(
            cor=opts.inner_color,
            blur=opts.inner_blur,
            opacidade=opts.inner_opacity
        )

        clone = copy.deepcopy(elem)
        clone.set('id', self.svg.get_unique_id('cpe-ig-'))

        estilo = inkex.Style()
        estilo['fill']   = self._hex_rgb(opts.inner_color)
        estilo['stroke'] = 'none'
        estilo['filter'] = f'url(#{fid})'

        clone.set('style', str(estilo))

        # Após o original → renderiza por cima (brilho interno visível)
        idx = list(grupo).index(elem)
        grupo.insert(idx + 1, clone)

    def _criar_filtro_inner_glow(self, cor, blur, opacidade) -> str:
        """
        Filtro SVG para brilho interno confinado à forma:
          feFlood → feComposite(in) → feGaussianBlur → feComposite(in)
        Retorna o id do <filter> criado em <defs>.
        """
        fid  = self.svg.get_unique_id('cpe-f-ig-')
        filt = etree.SubElement(self.svg.defs, _n('filter'))
        filt.set('id', fid)
        filt.set('x', '-10%');  filt.set('width',  '120%')
        filt.set('y', '-10%');  filt.set('height', '120%')
        filt.set('color-interpolation-filters', 'sRGB')

        r, g, b = int(cor.red), int(cor.green), int(cor.blue)

        flood = etree.SubElement(filt, _n('feFlood'))
        flood.set('flood-color', f'rgb({r},{g},{b})')
        flood.set('flood-opacity', f'{opacidade:.4f}')
        flood.set('result', 'flood')

        c1 = etree.SubElement(filt, _n('feComposite'))
        c1.set('in', 'flood');  c1.set('in2', 'SourceAlpha')
        c1.set('operator', 'in');  c1.set('result', 'clipped')

        gb = etree.SubElement(filt, _n('feGaussianBlur'))
        gb.set('in', 'clipped')
        gb.set('stdDeviation', f'{max(0.1, blur):.2f}')
        gb.set('result', 'blurred')

        c2 = etree.SubElement(filt, _n('feComposite'))
        c2.set('in', 'blurred');  c2.set('in2', 'SourceAlpha')
        c2.set('operator', 'in')

        return fid

    # ══════════════════════════════════════════════════════════════
    # EFEITO: GRADIENTE DE PREENCHIMENTO
    # ══════════════════════════════════════════════════════════════

    def _aplicar_gradiente_preenchimento(self, elem):
        """
        Substitui apenas o 'fill' do estilo do elemento original
        por uma referência a um gradiente criado em <defs>.
        Todos os outros atributos são preservados.
        """
        opts = self.options

        if opts.fill_gradient_type == 'radial':
            gid = self._criar_gradiente_radial(
                cor1=opts.fill_color1, cor2=opts.fill_color2,
                op1=opts.fill_opacity1, op2=opts.fill_opacity2,
                prefixo='cpe-rg-'
            )
        else:
            gid = self._criar_gradiente_linear(
                cor1=opts.fill_color1, cor2=opts.fill_color2,
                angulo=opts.fill_angle,
                op1=opts.fill_opacity1, op2=opts.fill_opacity2,
                prefixo='cpe-lg-'
            )

        estilo = inkex.Style(elem.get('style') or '')
        estilo['fill'] = f'url(#{gid})'
        elem.set('style', str(estilo))

    def _criar_gradiente_linear(self, cor1, cor2, angulo,
                                 op1, op2, prefixo) -> str:
        """
        <linearGradient> em gradientUnits="objectBoundingBox".
        Ângulo 0° = esquerda→direita; 90° = baixo→cima.
        """
        gid   = self.svg.get_unique_id(prefixo)
        rad   = math.radians(angulo)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        x1 = 0.5 - 0.5 * cos_a;  y1 = 0.5 + 0.5 * sin_a
        x2 = 0.5 + 0.5 * cos_a;  y2 = 0.5 - 0.5 * sin_a

        grad = etree.SubElement(self.svg.defs, _n('linearGradient'))
        grad.set('id', gid)
        grad.set('x1', f'{x1:.6f}');  grad.set('y1', f'{y1:.6f}')
        grad.set('x2', f'{x2:.6f}');  grad.set('y2', f'{y2:.6f}')
        grad.set('gradientUnits', 'objectBoundingBox')

        s1 = etree.SubElement(grad, _n('stop'))
        s1.set('offset', '0')
        s1.set('style', f'stop-color:{self._hex_rgb(cor1)};stop-opacity:{op1:.4f}')

        s2 = etree.SubElement(grad, _n('stop'))
        s2.set('offset', '1')
        s2.set('style', f'stop-color:{self._hex_rgb(cor2)};stop-opacity:{op2:.4f}')

        return gid

    def _criar_gradiente_radial(self, cor1, cor2,
                                 op1, op2, prefixo) -> str:
        """
        <radialGradient> centralizado em gradientUnits="objectBoundingBox".
        """
        gid  = self.svg.get_unique_id(prefixo)

        grad = etree.SubElement(self.svg.defs, _n('radialGradient'))
        grad.set('id', gid)
        grad.set('cx', '0.5');  grad.set('cy', '0.5')
        grad.set('r',  '0.5');  grad.set('fx', '0.5');  grad.set('fy', '0.5')
        grad.set('gradientUnits', 'objectBoundingBox')

        s1 = etree.SubElement(grad, _n('stop'))
        s1.set('offset', '0')
        s1.set('style', f'stop-color:{self._hex_rgb(cor1)};stop-opacity:{op1:.4f}')

        s2 = etree.SubElement(grad, _n('stop'))
        s2.set('offset', '1')
        s2.set('style', f'stop-color:{self._hex_rgb(cor2)};stop-opacity:{op2:.4f}')

        return gid

    # ──────────────────────────────────────────────────────────────
    # UTILITÁRIO — conversão de cor
    # ──────────────────────────────────────────────────────────────

    def _hex_rgb(self, cor) -> str:
        """inkex.Color → '#rrggbb' (descarta alpha). Seguro para inkex ≥ 1.0."""
        try:
            return f'#{int(cor.red):02x}{int(cor.green):02x}{int(cor.blue):02x}'
        except (AttributeError, TypeError, ValueError):
            return '#000000'


# ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    CPEEngine().run()
