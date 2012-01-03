# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""
Layout for page boxes and margin boxes.

"""

from __future__ import division

from ..formatting_structure import boxes, build
from .blocks import block_level_layout, block_level_height
from .percentages import resolve_percentages
from .preferred import inline_preferred_minimum_width, inline_preferred_width


def compute_fixed_dimension(box, outer, vertical, top_or_left):
    """
    Compute and set a margin box fixed dimension on ``box``, as described in:
    http://dev.w3.org/csswg/css3-page/#margin-constraints

    :param box:
        The margin box to work on
    :param outer:
        The target outer dimension (value of a page margin)
    :param vertical:
        True to set height, margin-top and margin-bottom; False for width,
        margin-left and margin-right
    :param top_or_left:
        True if the margin box in if the top half (for vertical==True) or
        left half (for vertical==False) of the page.
        This determines which margin should be 'auto' if the values are
        over-constrained. (Rule 3 of the algorithm.)
    """
    if vertical:
        margin_1 = box.margin_top
        margin_2 = box.margin_bottom
        inner = box.height
        padding_plus_border = (
            box.padding_top + box.padding_bottom +
            box.border_top_width + box.border_bottom_width)
    else:
        margin_1 = box.margin_left
        margin_2 = box.margin_right
        inner = box.width
        padding_plus_border = (
            box.padding_left + box.padding_right +
            box.border_left_width + box.border_right_width)

    # Rule 2
    total = padding_plus_border + sum(
        value for value in [margin_1, margin_2, inner]
        if value != 'auto')
    if total > outer:
        if margin_1 == 'auto':
            margin_1 = 0
        if margin_2 == 'auto':
            margin_2 = 0
        if inner == 'auto':
            # XXX this is not in the spec, but without it inner would end up
            # with negative value.
            # Instead, this will trigger rule 3 below.
            inner = 0
    # Rule 3
    if 'auto' not in [margin_1, margin_2, inner]:
        # Over-constrained
        if top_or_left:
            margin_1 = 'auto'
        else:
            margin_2 = 'auto'
    # Rule 4
    if [margin_1, margin_2, inner].count('auto') == 1:
        if inner == 'auto':
            inner = outer - padding_plus_border - margin_1 - margin_2
        elif margin_1 == 'auto':
            margin_1 = outer - padding_plus_border - margin_2 - inner
        elif margin_2 == 'auto':
            margin_2 = outer - padding_plus_border - margin_1 - inner
    # Rule 5
    if inner == 'auto':
        if margin_1 == 'auto':
            margin_1 = 0
        if margin_2 == 'auto':
            margin_2 = 0
        inner = outer - padding_plus_border - margin_1 - margin_2
    # Rule 6
    if margin_1 == 'auto' and margin_2 == 'auto':
        margin_1 = margin_2 = (outer - padding_plus_border - inner) / 2

    assert 'auto' not in [margin_1, margin_2, inner]
    # This should also be true, but may not be exact due to
    # floating point errors:
    #assert inner + padding_plus_border + margin_1 + margin_2 == outer
    if vertical:
        box.margin_top = margin_1
        box.margin_bottom = margin_2
        box.height = inner
    else:
        box.margin_left = margin_1
        box.margin_right = margin_2
        box.width = inner


def compute_variable_dimension(side_boxes, vertical, outer):
    """
    Compute and set a margin box fixed dimension on ``box``, as described in:
    http://dev.w3.org/csswg/css3-page/#margin-dimension

    :param side_boxes: Three boxes on a same side (as opposed to a corner.)
        A list of:
        - A @*-left or @*-top margin box
        - A @*-center or @*-middle margin box
        - A @*-right or @*-bottom margin box
    :param vertical:
        True to set height, margin-top and margin-bottom; False for width,
        margin-left and margin-right
    :param outer:
        The target total outer dimension (max box width or height)

    """
    box_a, box_b, box_c =  side_boxes

    padding_plus_border = 0
    for box in side_boxes:
        if vertical:
            box.margin_a = box.margin_top
            box.margin_b = box.margin_bottom
            # Inner dimension: that of the content area, as opposed to the
            # outer dimension: that of the margin area.
            box.inner = box.height
            if box.empty:
                # Rule 3
                box.padding_top = 0
                box.padding_bottom = 0
                box.border_top_width = 0
                box.border_bottom_width = 0
            else:
                padding_plus_border += (
                    box.padding_top + box.padding_bottom +
                    box.border_top_width + box.border_bottom_width)
        else:
            box.margin_a = box.margin_left
            box.margin_b = box.margin_right
            box.inner = box.width
            if box.empty:
                # Rule 3
                box.padding_left = 0
                box.padding_right = 0
                box.border_left_width = 0
                box.border_right_width = 0
            else:
                padding_plus_border += (
                    box.padding_left + box.padding_right +
                    box.border_left_width + box.border_right_width)


    if not box_b.empty:
        # TODO: rule 2
        # box_a.outer() == box_b.outer()
        pass

    # Target sum of all 'auto' values
    remaining = outer - padding_plus_border - sum(
        value
        for box in side_boxes
        for value in [box.margin_a, box.margin_b, box.inner]
        if value != 'auto')

    auto_inner_boxes = [box for box in side_boxes if box.inner == 'auto']
    if auto_inner_boxes:
        if vertical:
            # TODO: preferred (minimum) height???
            min_inners = [0 for box in auto_inner_boxes]
            max_inners = [float('inf') for _box in auto_inner_boxes]
        else:
            min_inners = map(inline_preferred_minimum_width, auto_inner_boxes)
            max_inners = map(inline_preferred_width, auto_inner_boxes)
        sum_min_inners = sum(min_inners)
        sum_max_inners = sum(max_inners)
        # Minimize margins while keeping inner dimensions within bounds
        if remaining < sum_min_inners:
            # minimum widths are bigger than the target sum for 'auto' values.
            # Use that, and 'auto' margins will be negative
            # Content will most likely overlap.
            for box, min_inner in zip(auto_inner_boxes, min_inners):
                # Rule 5
                box.inner = min_inner
            sum_margins = remaining - sum_min_inners
        elif remaining > sum_max_inners:
            for box, max_inner in zip(auto_inner_boxes, max_inners):
                # Rule 6
                box.inner = max_inner
            sum_margins = remaining - sum_max_inners
        else:
            sum_margins = 0
            sum_inners = remaining

#            if len(auto_inner_boxes) == 1:
#                auto_inner_boxes[0].inner == sum_inners
#            elif len(auto_inner_boxes) == 2:
#                # May not be the same as (box_a, box_b)
#                box_A, box_B = auto_inner_boxes
#                min_A, min_B = min_inners
#                max_A, max_B = max_inners
#                # sum(weights) == 1
#                if max_A == float('inf'):
#                    # XXX Until we have a better value for preferred heights...
#                    weight_A = 0.5
#                else:
#                    weight_A = max_A / sum_max_inners
#                # Ideal inner for A, to balance contents
#                target_A = sum_inners * weight_A
#                # Combine both ranges, assuming
#                #    box_A.inner + box_B.inner == sum_inners
#                min_A = max(min_A, sum_inners - max_B)
#                max_A = min(max_A, sum_inners - min_B)
#                # As close as possible to target_A, but within bounds
#                box_A.inner = min(max_A, max(min_A, target_A))
#                box_B.inner = sum_inners - box_A.inner
#            elif len(auto_inner_boxes) == 3:
#                # Order is preserved, so auto_inner_boxes
#                # is the same as [box_a, box_b, box_c]
#                min_A, min_B, min_C = min_inners
#                max_A, max_B, max_C = max_inners
#                # sum(weights) == 1
#                weight_A = max_A / sum_max_inners
#                weight_B = max_B / sum_max_inners
#                # Ideal inner for A and B, to balance contents
#                target_A = sum_inners * weight_A
#                target_B = sum_inners * weight_B
#                min_A = max(min_A, sum_inners - max_B - max_C)
#                max_A = min(max_A, sum_inners - min_B - max_C)
#                min_B = max(min_B, sum_inners - max_A - max_C)
#                max_B = min(max_B, sum_inners - min_A - max_C)

#                box_a.inner = min(max_A, max(min_A, target_A))
#                box_b.inner = min(max_B, max(min_B, target_B))
#                box_c.inner = sum_inners - box_a.inner - box_b.inner

            # Choose the inner dimension for all boxes with 'auto' but the last
            for box, max_inner, min_inner in zip(
                    auto_inner_boxes, max_inners, min_inners)[:-1]:
                if max_inner == float('inf'):
                    # XXX Until we have a better value for preferred heights...
                    weight = 1 / len(auto_inner_boxes)
                else:
                    weight = max_inner / sum_max_inners
                # Ideal inner for A, to balance contents
                target = sum_inners * weight
                # Combine both ranges, assuming
                #    sum(box.inner) == sum_inners
                others_sum_max = sum_max_inners - max_inner
                others_sum_min = sum_min_inners - min_inner
                min_inner = max(min_inner, sum_inners - others_sum_max)
                max_inner = min(max_inner, sum_inners - others_sum_min)
                # As close as possible to target_A, but within bounds
                box.inner = min(max_inner, max(min_inner, target))
            # The dimension for the last box is resolved with the target sum
            auto_inner_boxes[-1].inner = sum_inners - sum(
                box.inner for box in auto_inner_boxes[:-1])

    else:
        sum_margins = remaining

    if sum_margins == 0:
        # Valid even if there is no 'auto' margin
        each_auto_margin = 0
    else:
        num_auto_margins = sum(
            value == 'auto'  # boolean as int
            for box in side_boxes
            for value in (box.margin_a, box.margin_b)
        )
        if num_auto_margins == 0:
            # Over-constrained: ignore the computed values of these margins
            box_a.margin_b = 'auto'
            box_c.margin_a = 'auto'
            num_auto_margins = 2
        each_auto_margin = sum_margins / num_auto_margins
    for box in side_boxes:
        if box.margin_a == 'auto':
            box.margin_a = each_auto_margin
        if box.margin_b == 'auto':
            box.margin_b = each_auto_margin

    for box in side_boxes:
        if vertical:
            box.margin_top = box.margin_a
            box.margin_bottom = box.margin_a
            box.height = box.inner
        else:
            box.margin_left = box.margin_a
            box.margin_right = box.margin_a
            box.width = box.inner
        del box.margin_a
        del box.margin_b
        del box.inner


def empty_margin_boxes(document, page, page_type):
    """
    Return the margin boxes for this page that have their own dimensions and
    position set, but still need their content.

    Parameters: same as :func:`make_margin_boxes`.

    """
    # This is a closure only to make calls shorter
    def make_box(at_keyword, containing_block):
        """
        Return a margin box with resolved percentages, but that may still
        have 'auto' values.

        Return ``None`` if this margin box should not be generated.

        :param at_keyword: which margin box to return, eg. '@top-left'
        :param containing_block: as expected by :func:`resolve_percentages`.

        """
        style = document.style_for(page_type, at_keyword)
        if style is None:
            style = page.style.inherit_from()
        box = boxes.MarginBox(at_keyword, style)
        resolve_percentages(box, containing_block)
        # Empty boxes should not be generated, but they may be needed for
        # the layout of their neighbors.
        box.empty = (style.content in ('normal', 'none') and
                     style.width == 'auto')
        return box

    margin_top = page.margin_top
    margin_bottom = page.margin_bottom
    margin_left = page.margin_left
    margin_right = page.margin_right
    max_box_width = page.border_width()
    max_box_height = page.border_height()

    # bottom right corner of the border box
    page_end_x = margin_left + max_box_width
    page_end_y = margin_top + max_box_height

    # Margin box dimensions, described in
    # http://dev.w3.org/csswg/css3-page/#margin-box-dimensions

    # Order recommended on http://dev.w3.org/csswg/css3-page/#painting
    # center/middle on top (last in tree order), then corner, then others

    # First, boxes that are neither corner nor center/middle
    # Delay center/middle boxes
    generated_boxes = []
    delayed_boxes = []

    for prefix, vertical, containing_block, position_x, position_y in [
        ('top', False, (max_box_width, margin_top),
            margin_left, 0),
        ('bottom', False, (max_box_width, margin_bottom),
            margin_left, page_end_y),
        ('left', True, (margin_left, max_box_height),
            0, margin_top),
        ('right', True, (margin_right, max_box_height),
            page_end_x, margin_top),
    ]:
        if vertical:
            suffixes = ['top', 'middle', 'bottom']
            fixed_outer, variable_outer = containing_block
        else:
            suffixes = ['left', 'center', 'right']
            variable_outer, fixed_outer = containing_block
        side_boxes = [make_box('@%s-%s' % (prefix, suffix), containing_block)
                      for suffix in suffixes]
        if all(box.empty for box in side_boxes):
            continue
        # We need the three boxes together for the variable dimension:
        compute_variable_dimension(side_boxes, vertical, variable_outer)
        for box, delay in zip(side_boxes, [False, True, False]):
            if box.empty:
                continue
            compute_fixed_dimension(
                box, fixed_outer, not vertical, prefix in ['top', 'left'])
            box.position_x = position_x
            box.position_y = position_y
            if vertical:
                position_y += box.margin_height()
            else:
                position_x += box.margin_width()
            if delay:
                delayed_boxes.append(box)
            else:
                generated_boxes.append(box)

    # Corner boxes

    for at_keyword, cb_width, cb_height, position_x, position_y in [
        ('@top-left-corner', margin_left, margin_top, 0, 0),
        ('@top-right-corner', margin_right, margin_top, page_end_x, 0),
        ('@bottom-left-corner', margin_left, margin_bottom, 0, page_end_y),
        ('@bottom-right-corner', margin_right, margin_bottom,
            page_end_x, page_end_y),
    ]:
        box = make_box(at_keyword, (cb_width, cb_height))
        if box.empty:
            continue
        box.position_x = position_x
        box.position_y = position_y
        compute_fixed_dimension(box, cb_height, True, 'top' in at_keyword)
        compute_fixed_dimension(box, cb_width, False, 'left' in at_keyword)
        generated_boxes.append(box)

    generated_boxes.extend(delayed_boxes)
    return generated_boxes


def make_margin_boxes(document, page, page_type):
    """Yield laid-out margin boxes for this page.

    :param document: a :class:`Document` object
    :param page: a :class:`PageBox` object
    :param page_type: as returned by :func:`page_type_for_number`

    """
    for box in empty_margin_boxes(document, page, page_type):
        if box.style.content in ('normal', 'none'):
            continue
        # TODO: get actual counter values at the time of the last page break
        counter_values = {}
        quote_depth = [0]
        children = build.content_to_boxes(
            document, box.style, box, quote_depth, counter_values)
        box = box.copy_with_children(children)
        # content_to_boxes() only produces inline-level boxes, no need to
        # run other post-processors from build.build_formatting_structure()
        box = build.process_whitespace(box)
        box = build.inline_in_block(box)
        box, resume_at = block_level_height(document, box,
            max_position_y=float('inf'), skip_stack=None,
            device_size=page.style.size, page_is_empty=True)
        assert resume_at is None
        yield box


def page_type_for_number(page_number):
    """Return a page type such as ``'first_right_page'`` from a page number."""
    # First page is a right page.
    # TODO: this "should depend on the major writing direction of the
    # document".
    first_is_right = True

    is_right = (page_number % 2) == (1 if first_is_right else 0)
    page_type = 'right_page' if is_right else 'left_page'
    if page_number == 1:
        page_type = 'first_' + page_type
    return page_type


def make_page(document, page_number, resume_at):
    """Take just enough content from the beginning to fill one page.

    Return ``(page, finished)``. ``page`` is a laid out PageBox object
    and ``resume_at`` indicates where in the document to start the next page,
    or is ``None`` if this was the last page.

    :param document: a Document object
    :param page_number: integer, start at 1 for the first page
    :param resume_at: as returned by ``make_page()`` for the previous page,
                      or ``None`` for the first page.

    """
    root_box = document.formatting_structure
    page_type = page_type_for_number(page_number)
    style = document.style_for(page_type)
    page = boxes.PageBox(page_number, style, root_box.style.direction)

    device_size = page.style.size
    page.outer_width, page.outer_height = device_size

    resolve_percentages(page, device_size)

    page.position_x = 0
    page.position_y = 0
    page.width = page.outer_width - page.horizontal_surroundings()
    page.height = page.outer_height - page.vertical_surroundings()

    root_box.position_x = page.content_box_x()
    root_box.position_y = page.content_box_y()
    page_content_bottom = root_box.position_y + page.height
    initial_containing_block = page

    # TODO: handle cases where the root element is something else.
    # See http://www.w3.org/TR/CSS21/visuren.html#dis-pos-flo
    assert isinstance(root_box, boxes.BlockBox)
    root_box, resume_at = block_level_layout(
        document, root_box, page_content_bottom, resume_at,
        initial_containing_block, device_size, page_is_empty=True)
    assert root_box

    children = [root_box]
    children.extend(make_margin_boxes(document, page, page_type))

    page = page.copy_with_children(children)

    return page, resume_at
