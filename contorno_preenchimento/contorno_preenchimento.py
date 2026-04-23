#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   Contorno e Preenchimento Avançado — Extensão Inkscape 1.4+    ║
║   Licença: GPL v2+  |  Compatível: Linux, Windows, macOS        ║
╚══════════════════════════════════════════════════════════════════╝

Recursos não-destrutivos:
  • Contorno (stroke) com cor sólida ou gradiente linear
  • Brilho Externo (Outer Glow) com desfoque e expansão
  • Brilho Interno (Inner Glow) com clip por forma
  • Gradiente de Preenchimento: linear (com ângulo) ou radial

Estrutura não-destrutiva:
  Todos os efeitos são aplicados em cópias do objeto original
  agrupadas num wrapper <g id="cpe-…">.  O objeto original nunca
  é destruído; apenas o fill é trocado quando o gradiente de
  preenchimento está activo (comportamento documentado).
"""

import math
import copy
import inkex
from inkex import Group
from lxml import etree

# ─────────────────────────────────────────────────────────────────
# Constantes de namespace
# ─────────────────────────────────────────────────────────────────
SVG_NS   = "http://www.w3.org/2000/svg"
INKNS    = "http://www.inkscape.org/namespaces/inkscape"


def _n(tag: str) -> str:
    """Retorna tag qualificada com namespace SVG."""
    return f'{{{SVG_NS}}}{tag}'


# ═════════════════════════════════════════════════════════════════
class ContornoPreenchimento(inkex.EffectExtension):
    """
    Extensão principal: herda de inkex.EffectExtension (v1.4+).
    Aplica efeitos visuais não-destrutivos a objetos seleccionados.
    """

    # ──────────────────────────────────────────────────────────────
    # 1. DEFINIÇÃO DE ARGUMENTOS (mapeados ao .inx)
    # ──────────────────────────────────────────────────────────────
    def add_arguments(self, pars):
        """Declara todos os parâmetros da interface GTK."""

        # Controle interno de aba activa
        pars.add_argument("--tab", type=str, dest="tab",
                          default="aba_contorno")

        # ── Contorno ───────────────────────────────────────────────
        pars.add_argument("--enable_stroke", type=inkex.Boolean,
                          dest="enable_stroke", default=True)
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

        # ── Brilho Externo ─────────────────────────────────────────
        pars.add_argument("--enable_outer_glow", type=inkex.Boolean,
                          dest="enable_outer_glow", default=False)
        pars.add_argument("--outer_color", type=inkex.Color,
                          dest="outer_color",
                          default=inkex.Color("#ffff00"))
        pars.add_argument("--outer_blur", type=float,
                          dest="outer_blur", default=8.0)
        pars.add_argument("--outer_spread", type=float,
                          dest="outer_spread", default=0.0)
        pars.add_argument("--outer_opacity", type=float,
                          dest="outer_opacity", default=0.8)

        # ── Brilho Interno ─────────────────────────────────────────
        pars.add_argument("--enable_inner_glow", type=inkex.Boolean,
                          dest="enable_inner_glow", default=False)
        pars.add_argument("--inner_color", type=inkex.Color,
                          dest="inner_color",
                          default=inkex.Color("#00ffff"))
        pars.add_argument("--inner_blur", type=float,
                          dest="inner_blur", default=8.0)
        pars.add_argument("--inner_opacity", type=float,
                          dest="inner_opacity", default=0.8)

        # ── Gradiente de Preenchimento ─────────────────────────────
        pars.add_argument("--enable_fill_gradient", type=inkex.Boolean,
                          dest="enable_fill_gradient", default=False)
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
    # 2. MÉTODO PRINCIPAL
    # ──────────────────────────────────────────────────────────────
    def effect(self):
        """
        Ponto de entrada da extensão.
        Valida a selecção e itera sobre os elementos seleccionados.
        """
        if not self.svg.selection:
            inkex.errormsg(
                "⚠  Nenhum objecto seleccionado!\n\n"
                "Seleccione um ou mais objectos no canvas\n"
                "antes de aplicar esta extensão.\n\n"
                "Dica: use Ctrl+A para seleccionar tudo."
            )
            return

        for elem in list(self.svg.selection.values()):
            try:
                self._processar_elemento(elem)
            except Exception as err:
                inkex.errormsg(
                    f"Erro ao processar o elemento "
                    f"'{elem.get_id() or type(elem).__name__}':\n{err}"
                )

    # ──────────────────────────────────────────────────────────────
    # 3. PROCESSAMENTO DE ELEMENTO — orchestrador
    # ──────────────────────────────────────────────────────────────
    def _processar_elemento(self, elem):
        """
        Envolve o elemento num grupo <g id="cpe-…"> e delega
        a cada método de efeito na ordem correcta de empilhamento:

            [0] Brilho Externo  ← mais abaixo (renderizado primeiro)
            [1] Contorno
            [2] Original         ← preservado intacto
            [3] Brilho Interno  ← mais acima
        """
        opts = self.options
        pai  = elem.getparent()
        if pai is None:
            return

        # Cria o grupo wrapper
        grupo = Group()
        grupo.set('id', self.svg.get_unique_id('cpe-'))
        grupo.set(f'{{{INKNS}}}label', 'CPE: Efeitos Visuais')
        grupo.set(f'{{{INKNS}}}groupmode', 'layer')

        # Substitui o elemento pelo grupo no documento
        idx = list(pai).index(elem)
        pai.insert(idx, grupo)
        pai.remove(elem)
        grupo.append(elem)   # original fica dentro do grupo

        # Aplica efeitos na ordem de empilhamento
        if opts.enable_outer_glow:
            self._aplicar_brilho_externo(elem, grupo)

        if opts.enable_stroke:
            self._aplicar_contorno(elem, grupo)

        if opts.enable_fill_gradient:
            self._aplicar_gradiente_preenchimento(elem)

        if opts.enable_inner_glow:
            self._aplicar_brilho_interno(elem, grupo)

    # ──────────────────────────────────────────────────────────────
    # 4. CONTORNO
    # ──────────────────────────────────────────────────────────────
    def _aplicar_contorno(self, elem, grupo):
        """
        Cria uma cópia profunda do elemento, configurada apenas
        com stroke (fill=none) e insere-a abaixo do original.
        Suporta cor sólida ou gradiente linear no traço.
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
            # Gradiente linear aplicado ao stroke
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

        # Insere imediatamente antes do original (uma posição abaixo)
        grupo.insert(list(grupo).index(elem), clone)

    # ──────────────────────────────────────────────────────────────
    # 5. BRILHO EXTERNO
    # ──────────────────────────────────────────────────────────────
    def _aplicar_brilho_externo(self, elem, grupo):
        """
        Cria clone colorido + filtro de desfoque gaussiano.
        Posicionado no índice 0 do grupo (mais abaixo de tudo).
        """
        opts   = self.options
        fid    = self._criar_filtro_outer_glow(
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
        grupo.insert(0, clone)   # mais abaixo no grupo

    def _criar_filtro_outer_glow(self, cor, blur, opacidade) -> str:
        """
        Filtro SVG para brilho externo:
          SourceGraphic → feColorMatrix (coloriza) → feGaussianBlur
        Retorna o id do filtro criado em <defs>.
        """
        fid  = self.svg.get_unique_id('cpe-f-og-')
        filt = etree.SubElement(self.svg.defs, _n('filter'))
        filt.set('id', fid)
        filt.set('x', '-100%')
        filt.set('y', '-100%')
        filt.set('width', '300%')
        filt.set('height', '300%')
        filt.set('color-interpolation-filters', 'sRGB')

        r = int(cor.red)   / 255.0
        g = int(cor.green) / 255.0
        b = int(cor.blue)  / 255.0

        # Substitui a cor mantendo o canal alpha da forma original
        cm = etree.SubElement(filt, _n('feColorMatrix'))
        cm.set('type', 'matrix')
        cm.set('in', 'SourceGraphic')
        cm.set('values', (
            f'0 0 0 0 {r:.4f}  '
            f'0 0 0 0 {g:.4f}  '
            f'0 0 0 0 {b:.4f}  '
            f'0 0 0 {opacidade:.4f} 0'
        ))
        cm.set('result', 'colorized')

        # Desfoque gaussiano para criar a aura
        gb = etree.SubElement(filt, _n('feGaussianBlur'))
        gb.set('in', 'colorized')
        gb.set('stdDeviation', f'{max(0.1, blur):.2f}')

        return fid

    # ──────────────────────────────────────────────────────────────
    # 6. BRILHO INTERNO
    # ──────────────────────────────────────────────────────────────
    def _aplicar_brilho_interno(self, elem, grupo):
        """
        Cria clone com filtro de brilho interno, inserido após
        o original no grupo (acima na ordem de renderização).
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

        # Insere DEPOIS do original → acima na renderização
        idx = list(grupo).index(elem)
        grupo.insert(idx + 1, clone)

    def _criar_filtro_inner_glow(self, cor, blur, opacidade) -> str:
        """
        Filtro SVG para brilho interno.
        Técnica: feFlood → clip por SourceAlpha → feGaussianBlur → clip.
        O resultado fica sempre confinado ao interior da forma.
        Retorna o id do filtro criado em <defs>.
        """
        fid  = self.svg.get_unique_id('cpe-f-ig-')
        filt = etree.SubElement(self.svg.defs, _n('filter'))
        filt.set('id', fid)
        filt.set('x', '-10%')
        filt.set('y', '-10%')
        filt.set('width', '120%')
        filt.set('height', '120%')
        filt.set('color-interpolation-filters', 'sRGB')

        r = int(cor.red)
        g = int(cor.green)
        b = int(cor.blue)

        # Passo 1 — inunda com a cor do brilho
        flood = etree.SubElement(filt, _n('feFlood'))
        flood.set('flood-color', f'rgb({r},{g},{b})')
        flood.set('flood-opacity', f'{opacidade:.4f}')
        flood.set('result', 'flood')

        # Passo 2 — recorta pelo perfil do objecto
        c1 = etree.SubElement(filt, _n('feComposite'))
        c1.set('in', 'flood')
        c1.set('in2', 'SourceAlpha')
        c1.set('operator', 'in')
        c1.set('result', 'clipped')

        # Passo 3 — aplica desfoque gaussiano
        gb = etree.SubElement(filt, _n('feGaussianBlur'))
        gb.set('in', 'clipped')
        gb.set('stdDeviation', f'{max(0.1, blur):.2f}')
        gb.set('result', 'blurred')

        # Passo 4 — recorta novamente para não vazar para fora
        c2 = etree.SubElement(filt, _n('feComposite'))
        c2.set('in', 'blurred')
        c2.set('in2', 'SourceAlpha')
        c2.set('operator', 'in')

        return fid

    # ──────────────────────────────────────────────────────────────
    # 7. GRADIENTE DE PREENCHIMENTO
    # ──────────────────────────────────────────────────────────────
    def _aplicar_gradiente_preenchimento(self, elem):
        """
        Aplica gradiente (linear ou radial) ao fill do elemento.
        Apenas o atributo 'fill' do estilo é alterado; todos os
        outros atributos do elemento são preservados.
        """
        opts = self.options

        if opts.fill_gradient_type == 'radial':
            gid = self._criar_gradiente_radial(
                cor1=opts.fill_color1,
                cor2=opts.fill_color2,
                op1=opts.fill_opacity1,
                op2=opts.fill_opacity2,
                prefixo='cpe-rg-'
            )
        else:
            gid = self._criar_gradiente_linear(
                cor1=opts.fill_color1,
                cor2=opts.fill_color2,
                angulo=opts.fill_angle,
                op1=opts.fill_opacity1,
                op2=opts.fill_opacity2,
                prefixo='cpe-lg-'
            )

        # Altera APENAS o fill, mantendo o restante do estilo
        estilo = inkex.Style(elem.get('style') or '')
        estilo['fill'] = f'url(#{gid})'
        elem.set('style', str(estilo))

    def _criar_gradiente_linear(self, cor1, cor2, angulo,
                                 op1, op2, prefixo) -> str:
        """
        Cria <linearGradient> em <defs>.
        O ângulo 0° → esquerda→direita; 90° → baixo→cima.
        Usa gradientUnits="objectBoundingBox" para escalar com o shape.
        """
        gid     = self.svg.get_unique_id(prefixo)
        rad     = math.radians(angulo)
        cos_a   = math.cos(rad)
        sin_a   = math.sin(rad)

        # Calcula pontos de início e fim no espaço [0,1]²
        x1 = 0.5 - 0.5 * cos_a
        y1 = 0.5 + 0.5 * sin_a
        x2 = 0.5 + 0.5 * cos_a
        y2 = 0.5 - 0.5 * sin_a

        grad = etree.SubElement(self.svg.defs, _n('linearGradient'))
        grad.set('id', gid)
        grad.set('x1', f'{x1:.6f}')
        grad.set('y1', f'{y1:.6f}')
        grad.set('x2', f'{x2:.6f}')
        grad.set('y2', f'{y2:.6f}')
        grad.set('gradientUnits', 'objectBoundingBox')

        s1 = etree.SubElement(grad, _n('stop'))
        s1.set('offset', '0')
        s1.set('style',
               f'stop-color:{self._hex_rgb(cor1)};'
               f'stop-opacity:{op1:.4f}')

        s2 = etree.SubElement(grad, _n('stop'))
        s2.set('offset', '1')
        s2.set('style',
               f'stop-color:{self._hex_rgb(cor2)};'
               f'stop-opacity:{op2:.4f}')

        return gid

    def _criar_gradiente_radial(self, cor1, cor2,
                                  op1, op2, prefixo) -> str:
        """
        Cria <radialGradient> em <defs>.
        Centro e raio fixos no espaço objectBoundingBox [0,1]².
        """
        gid  = self.svg.get_unique_id(prefixo)

        grad = etree.SubElement(self.svg.defs, _n('radialGradient'))
        grad.set('id', gid)
        grad.set('cx', '0.5')
        grad.set('cy', '0.5')
        grad.set('r',  '0.5')
        grad.set('fx', '0.5')
        grad.set('fy', '0.5')
        grad.set('gradientUnits', 'objectBoundingBox')

        s1 = etree.SubElement(grad, _n('stop'))
        s1.set('offset', '0')
        s1.set('style',
               f'stop-color:{self._hex_rgb(cor1)};'
               f'stop-opacity:{op1:.4f}')

        s2 = etree.SubElement(grad, _n('stop'))
        s2.set('offset', '1')
        s2.set('style',
               f'stop-color:{self._hex_rgb(cor2)};'
               f'stop-opacity:{op2:.4f}')

        return gid

    # ──────────────────────────────────────────────────────────────
    # 8. UTILITÁRIOS
    # ──────────────────────────────────────────────────────────────
    def _hex_rgb(self, cor) -> str:
        """
        Converte inkex.Color → '#rrggbb' (sem alpha).
        Seguro para qualquer versão do inkex ≥ 1.0.
        """
        try:
            r = int(cor.red)
            g = int(cor.green)
            b = int(cor.blue)
            return f'#{r:02x}{g:02x}{b:02x}'
        except (AttributeError, TypeError, ValueError):
            return '#000000'


# ─────────────────────────────────────────────────────────────────
# Ponto de entrada quando executado directamente pelo Inkscape
# ─────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    ContornoPreenchimento().run()
