# Author Contact + ILL Request Drafts

Written 2026-07-27, per `docs/WEEK3-4_PLAN.md` Part 1, P5. **Off the critical path for
everything in this plan** -- Week 3/4 do not wait on any reply. If a preprint or reply
arrives, it strengthens the Related Work section and possibly the Day 21 cross-validation
(Tier 2); if nothing arrives, nothing here was blocking.

Total time to send: ~20 minutes (3 emails + 1 library form). Claude drafted the text; Nishi
sends it, since it needs his name, school affiliation, and actual email account.

## Before sending: fill in the two placeholders

Each draft below has a `[CORRESPONDING AUTHOR EMAIL]` placeholder. To find the real address
(2 minutes per paper): open the paper's own abstract/landing page (linked in each section)
-- published papers almost always list a corresponding author's email directly on that page
or in the PDF's first page. If it's not there, use the university department contact search
linked in each section.

---

## 1. Köning, Wimmer & Witkovský (2014) -- highest priority

The Day 19-20 method (Köning/Wimmer/Witkovský nonlinear-constraint EIV fit) is currently
implemented as "the algorithm family, not a faithful reproduction of this paper's specific
tuning choices" (per `notes/koning_2014.md`) because the original paper is paywalled. A
reply here has the most direct value of the three.

**Paper:** Köning, R., Wimmer, G., & Witkovský, V. (2014). *Ellipse fitting by nonlinear
constraints to demodulate quadrature homodyne interferometer signals and to determine the
statistical uncertainty of the interferometric phase.* Measurement Science and Technology,
25(11), 115001. DOI: 10.1088/0957-0233/25/11/115001.
Landing page: https://iopscience.iop.org/article/10.1088/0957-0233/25/11/115001

**Corresponding author (likely):** Viktor Witkovský -- confirmed affiliated with PTB
(Physikalisch-Technische Bundesanstalt), Braunschweig, Germany (also affiliated with the
Slovak Academy of Sciences on other publications; check the paper's own author-affiliation
footnote for which is listed for this specific paper). PTB general contact search:
https://www.ptb.de/cms/en/meta/search-contact.html

**Draft:**

> Subject: Preprint request -- "Ellipse fitting by nonlinear constraints" (Meas. Sci.
> Technol. 2014), for an open benchmark project
>
> Dear Dr. Witkovský,
>
> My name is Nishad Suresh, a high school student building an open-source benchmark
> (hoqi-bench, github.com/nishadsuresh/hoqi-bench) comparing phase-recovery methods for
> homodyne quadrature interferometry, including an implementation of the nonlinear-constraint
> errors-in-variables approach from your 2014 paper with Köning and Wimmer.
>
> I was able to understand the algorithm family through the OEFPIL package documentation,
> but I don't have access to the original paper's full text (Measurement Science and
> Technology, DOI 10.1088/0957-0233/25/11/115001) and would like to implement it as
> faithfully as possible to your original tuning choices, rather than only an approximation
> of the general method.
>
> Would you be willing to share a preprint or author's copy of the paper? I'd be glad to
> credit it directly in the project's documentation and cite it appropriately.
>
> Thank you for your time,
> Nishad Suresh
> [your email] / github.com/nishadsuresh
>
> [CORRESPONDING AUTHOR EMAIL]

---

## 2. Collett & Tee (2014) -- closest prior art

**Paper:** Collett, M. J. & Tee, G. J. (2014). *Ellipse fitting for interferometry. Part 1:
static methods.* J. Opt. Soc. Am. A, 31(12), 2573-2583.
Landing page: https://opg.optica.org/josaa/abstract.cfm?uri=josaa-31-12-2573

**Authors' affiliation (confirmed via web search):** M. J. Collett, Department of Physics,
University of Auckland, Private Bag 92019, Auckland 1142, New Zealand; G. J. Tee, Department
of Mathematics, same institution. University of Auckland staff directory:
https://www.auckland.ac.nz/en/science/about-the-faculty/physics/our-people.html (Physics)
and the Mathematics department's equivalent page.

**Draft:**

> Subject: Preprint request -- "Ellipse fitting for interferometry, Part 1" (JOSA A 2014)
>
> Dear Prof. Collett,
>
> My name is Nishad Suresh, a high school student building an open-source benchmark
> (hoqi-bench, github.com/nishadsuresh/hoqi-bench) comparing ellipse-fitting methods for
> homodyne quadrature interferometry -- Kasa, Heydemann, Halir & Flusser, Fitzgibbon, Taubin,
> and Köning/Wimmer/Witkovský's nonlinear-constraint fit.
>
> Your 2014 paper with G. J. Tee (JOSA A 31(12), 2573-2583) appears to be the closest prior
> comparison of multiple ellipse-fitting methods specifically in an interferometry context,
> but it's paywalled and I've only been able to read the abstract. I'd like to compare my
> project's related-work framing against your actual results, and ideally reproduce a
> qualitative finding from your comparison as a validation check.
>
> Would you be willing to share a preprint or author's copy? I'd be glad to credit and cite
> it properly.
>
> Thank you for your time,
> Nishad Suresh
> [your email] / github.com/nishadsuresh
>
> [CORRESPONDING AUTHOR EMAIL]

---

## 3. Collett & Watkins (2015) -- companion paper

**Paper:** Collett, M. J. & Watkins, S. (2015). *Ellipse fitting for interferometry. Part 3:
dynamic method.* J. Opt. Soc. Am. A, 32(3), 491.
Landing page: https://opg.optica.org/josaa/abstract.cfm?uri=josaa-32-3-491

Note: there is also a **Part 2** ("experimental realization," Appl. Opt. 53(32):7697, 2014)
in the same series, not previously logged in `notes/related_work_table.md` -- worth adding to
that table regardless of whether this email is sent, since it's a real, findable piece of the
same series.

**Likely same corresponding author as #2** (M. J. Collett, University of Auckland Physics) --
a single combined email covering both papers is reasonable and saves a message; a merged
draft is below as an alternative to sending #2 and #3 separately.

**Combined draft (use instead of #2 above if preferred):**

> Subject: Preprint request -- "Ellipse fitting for interferometry" series, Parts 1 and 3
> (JOSA A 2014-2015)
>
> Dear Prof. Collett,
>
> My name is Nishad Suresh, a high school student building an open-source benchmark
> (hoqi-bench, github.com/nishadsuresh/hoqi-bench) comparing ellipse-fitting methods for
> homodyne quadrature interferometry.
>
> Your "Ellipse fitting for interferometry" series (Part 1, JOSA A 31(12):2573, with G. J.
> Tee; Part 3, JOSA A 32(3):491, with S. Watkins) appears to be the closest prior comparison
> of multiple ellipse-fitting methods in an interferometry context, but both are paywalled
> and I've only read the abstracts. I'd like to compare my project's related-work framing
> against your actual results, and ideally reproduce a qualitative finding as a validation
> check.
>
> Would you be willing to share preprints or author's copies of either or both parts? I'd be
> glad to credit and cite them properly.
>
> Thank you for your time,
> Nishad Suresh
> [your email] / github.com/nishadsuresh
>
> [CORRESPONDING AUTHOR EMAIL]

---

## 4. School librarian ILL (interlibrary loan) request

For whichever of the above don't get a reply. Most school/public library systems have a
simple ILL request form; if a specific one isn't already known, this text works as a general
request to a librarian directly.

> Subject: Interlibrary loan request -- 3 physics/optics journal articles
>
> Hi [librarian name],
>
> Could you help me request interlibrary loan copies of three paywalled journal articles for
> a research project? All three are in optics/measurement science:
>
> 1. Köning, R., Wimmer, G., & Witkovský, V. (2014). "Ellipse fitting by nonlinear
>    constraints to demodulate quadrature homodyne interferometer signals..." Measurement
>    Science and Technology, 25(11), 115001. DOI: 10.1088/0957-0233/25/11/115001
> 2. Collett, M. J. & Tee, G. J. (2014). "Ellipse fitting for interferometry. Part 1: static
>    methods." J. Opt. Soc. Am. A, 31(12), 2573-2583.
> 3. Collett, M. J. & Watkins, S. (2015). "Ellipse fitting for interferometry. Part 3:
>    dynamic method." J. Opt. Soc. Am. A, 32(3), 491.
>
> Thank you!
> Nishad Suresh

---

## Status

Not yet sent as of 2026-07-27 (drafted only). Update this section with dates sent and any
replies received -- if a preprint arrives, note it here and update
`notes/related_work_table.md` / `notes/koning_2014.md`'s access-level accordingly.
