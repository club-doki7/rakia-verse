#import "@preview/cuti:0.4.0": cn-fakebold as cuti

#let zh-fonts = ("Libertinus Serif", "Noto Serif SC", "Noto Serif CJK SC", "Scheherazade New")
#let fangsong-fonts = ("Libertinus Serif", "Zhuque Fangsong (technical preview)", "Scheherazade New")

#let chapter(title: "", id: none, meta: none, body) = {
  set page(paper: "a4", numbering: "1", margin: (top: 2.25cm, bottom: 2.25cm))
  set text(font: zh-fonts, lang: "zh", size: 11pt)
  show heading.where(level: 1): set align(center)
  counter(footnote).update(1)

  [
    = #title #if id != none { label(id) }
    #v(1em)

    #body
  ]
}

#let section(id: none, meta: none, body) = [
  #if id != none { label(id) } #body
]
