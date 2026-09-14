"""Local LIVE/EXPLORE review with deterministic observation responses.

No weather-service calls: the observation endpoint is intercepted in the browser.
Only test responses receive accelerated polling and debug handles.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path

from playwright.sync_api import sync_playwright


class Feed:
    def __init__(self, age=120, direction=45, speed=18.2, status='live'):
        self.age, self.direction, self.speed, self.status = age, direction, speed, status
        self.calls = 0

    def reply(self, route):
        self.calls += 1
        now = datetime.now(timezone.utc)
        data = {'status': self.status, 'server_time': now.isoformat(),
                'stale_after_seconds': 360, 'poll_interval_seconds': 60,
                'observation': None if self.status == 'unavailable' else {
                    'station': 'pearl', 'observed_at': (now - timedelta(seconds=self.age)).isoformat(),
                    'direction_deg': self.direction, 'speed_kts': self.speed}}
        route.fulfill(status=503 if self.status == 'unavailable' else 200,
                      content_type='application/json', body=json.dumps(data))


def setup(browser, base_url, width=390, height=844, reduced=False, poll=None, feed=None):
    context = browser.new_context(viewport={'width': width, 'height': height},
                                  device_scale_factor=3, is_mobile=width < 1000, has_touch=True,
                                  reduced_motion='reduce' if reduced else 'no-preference')
    page = context.new_page()
    feed = feed or Feed()
    page.route('**/wind-map/observation', feed.reply)
    def capture(route):
        response = route.fetch()
        hook = '''
L.Map.addInitHook(function () { window.reviewMap = this; });
const RealWind = window.PearlWindOverlay;
window.PearlWindOverlay = class extends RealWind { constructor(...args) { super(...args); window.reviewWind = this; } };
const RealControl = window.PearlWindController;
window.PearlWindController = class extends RealControl { constructor(...args) { super(...args); window.reviewController = this; } };
'''
        if poll is not None:
            hook += f"const tag = document.getElementById('map-config'); const cfg = JSON.parse(tag.textContent); cfg.pollSeconds = {poll}; tag.textContent = JSON.stringify(cfg);\n"
        route.fulfill(response=response, body=hook + response.text())
    page.route('**/wind-map/map.js', capture)
    errors, external = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda request: external.append(request.url) if not request.url.startswith(base_url) else None)
    page.goto(base_url + '/wind-map')
    page.wait_for_selector('#bermuda-map[data-ready="true"]')
    page.wait_for_function("document.querySelector('#wind-state').textContent !== 'PEARL · CONNECTING'")
    return context, page, feed, errors, external


def centre(page):
    return page.evaluate('({centre: window.reviewMap.getCenter(), zoom: window.reviewMap.getZoom()})')


def same_view(before, page):
    after = centre(page)
    assert abs(before['centre']['lat'] - after['centre']['lat']) < .0001, (before, after)
    assert abs(before['centre']['lng'] - after['centre']['lng']) < .0001, (before, after)
    assert before['zoom'] == after['zoom']


def dial_point(page, bearing):
    rect = page.locator('#direction-dial').bounding_box()
    radius = rect['width'] * .34
    rad = math.radians(bearing)
    return rect['x'] + rect['width']/2 + math.sin(rad)*radius, rect['y'] + rect['height']/2 - math.cos(rad)*radius


def assert_bearing(page, expected):
    actual = float(page.locator('.wind-canvas').get_attribute('data-from'))
    assert abs((actual - expected + 180) % 360 - 180) < 1, (actual, expected)
    toward = float(page.locator('.wind-canvas').get_attribute('data-toward'))
    assert abs((toward - actual + 180) % 360) < .001


def review(base_url, output, engine):
    output.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as playwright:
        browser = (playwright.webkit.launch() if engine == 'webkit'
                   else playwright.chromium.launch(channel='chrome', headless=True))
        for name, width, height in [('portrait', 390, 844), ('small-phone', 320, 568),
                                    ('landscape', 844, 390), ('desktop', 1440, 900)]:
            context, page, feed, errors, external = setup(browser, base_url, width, height)
            assert page.locator('#wind-state').inner_text() == 'PEARL LIVE'
            assert page.locator('#wind-reading').inner_text() == 'From 45° NE · 18.2 kt'
            assert page.evaluate('JSON.parse(document.querySelector("#map-config").textContent).pollSeconds') == 60
            assert 'Observed' in page.locator('#wind-age').inner_text()
            canvas = page.locator('.wind-canvas')
            assert page.locator('canvas').count() == 1
            assert canvas.get_attribute('data-motion') == 'running'
            assert float(canvas.get_attribute('data-pixel-ratio')) <= 1.5
            assert_bearing(page, 45)
            first = canvas.evaluate('(c) => c.toDataURL()')
            page.wait_for_timeout(150)
            assert first != canvas.evaluate('(c) => c.toDataURL()')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(output / f'{engine}-{name}-live.jpg'), type='jpeg', quality=90)
            marker = page.locator('[data-station="pearl"]')
            marker.click()
            assert '32.2917533' in page.locator('.leaflet-popup').inner_text()
            page.locator('.leaflet-popup-close-button').click()
            page.get_by_role('button', name='Zoom in', exact=True).click()
            page.wait_for_timeout(350)
            page.evaluate('window.reviewMap.panBy([50, 20], {animate: false})')
            map_box = page.locator('#bermuda-map').bounding_box()
            wind_box = canvas.bounding_box()
            for axis in ['x', 'y', 'width', 'height']:
                assert abs(map_box[axis] - wind_box[axis]) < 1
            view = centre(page)
            page.get_by_role('button', name='Explore', exact=True).click()
            assert page.locator('#wind-state').inner_text() == 'EXPLORE'
            assert_bearing(page, 45)
            same_view(view, page)
            page.get_by_role('button', name='Show Bermuda', exact=True).click()
            page.screenshot(path=str(output / f'{engine}-{name}-explore.jpg'), type='jpeg', quality=90)
            page.route('**/winds/1', lambda route: route.fulfill(body='Pearl return target', content_type='text/html'))
            page.locator('#back-to-pearl').click()
            page.wait_for_url('**/winds/1')
            assert page.evaluate("sessionStorage.getItem('pearl_scroll_to_top_after_refresh')") == '1'
            assert not errors, errors
            assert not external, external
            results.append({'viewport': name, 'live_explore_navigation': 'passed', 'errors': errors, 'external': external})
            context.close()

        # Continuous control interaction, actual polling, preserved view and lifecycle.
        context, page, feed, errors, external = setup(browser, base_url, poll=.2)
        feed.direction, feed.speed = 135, 9.7
        page.wait_for_function("document.querySelector('.wind-canvas').dataset.from === '135'")
        assert page.locator('#wind-reading').inner_text() == 'From 135° SE · 9.7 kt'
        page.evaluate('window.reviewMap.setView([32.30, -64.81], 12.5, {animate: false})')
        view = centre(page)
        page.get_by_role('button', name='Explore', exact=True).click()
        page.evaluate('window.originalParticles = window.reviewWind.particles')
        x, y = dial_point(page, 135)
        page.mouse.move(x, y)
        page.mouse.down()
        x, y = dial_point(page, 122.3)
        page.mouse.move(x, y, steps=8)
        assert_bearing(page, 122.3)  # Before release, not a change-only handler.
        assert page.locator('#wind-reading').inner_text() == '122° · ESE'
        for angle in [359.5, .5]:
            x, y = dial_point(page, angle)
            page.mouse.move(x, y)
            assert_bearing(page, angle)
        page.mouse.up()
        assert page.evaluate('window.originalParticles === window.reviewWind.particles')
        same_view(view, page)
        if engine == 'chrome':
            session = context.new_cdp_session(page)
            x, y = dial_point(page, .5)
            session.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y}]})
            x, y = dial_point(page, 122.3)
            session.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x, 'y': y}]})
            assert_bearing(page, 122.3)
            session.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        calls = feed.calls
        page.wait_for_timeout(400)
        assert feed.calls == calls, 'Explore must pause LIVE polling'
        selected = float(page.locator('.wind-canvas').get_attribute('data-from'))
        page.set_viewport_size({'width': 844, 'height': 390})
        page.wait_for_timeout(250)
        assert page.locator('#direction-range').is_visible()
        assert not page.locator('#direction-dial').is_visible()
        assert_bearing(page, selected)
        same_view(view, page)
        slider = page.locator('#direction-range')
        rect = slider.bounding_box()
        page.mouse.move(rect['x'] + 18, rect['y'] + rect['height']/2)
        page.mouse.down()
        page.mouse.move(rect['x'] + rect['width']*.7, rect['y'] + rect['height']/2, steps=8)
        selected = float(slider.input_value())
        assert_bearing(page, selected)
        assert selected > 180
        page.mouse.up()
        slider.focus()
        page.keyboard.press('End')
        assert_bearing(page, 359)
        page.keyboard.press('ArrowRight')
        assert_bearing(page, 0)
        page.set_viewport_size({'width': 390, 'height': 844})
        page.wait_for_timeout(250)
        assert_bearing(page, 0)
        same_view(view, page)
        feed.direction, feed.speed = 270, 12.4
        page.get_by_role('button', name='Back to Live', exact=True).click()
        page.wait_for_function("document.querySelector('.wind-canvas').dataset.from === '270'")
        assert page.locator('#wind-state').inner_text() == 'PEARL LIVE'
        assert page.locator('#explore-controls').is_hidden()
        same_view(view, page)
        page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide'))")
        assert page.locator('.wind-canvas').get_attribute('data-motion') == 'paused'
        calls = feed.calls
        page.wait_for_timeout(400)
        assert feed.calls == calls
        page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow'))")
        page.wait_for_function("document.querySelector('.wind-canvas').dataset.motion === 'running'")
        assert not errors, errors
        results.append({'continuous_dial_slider_wrap_poll_resume_pan_zoom': 'passed', 'chrome_touch_drag': engine == 'chrome'})
        context.close()

        # Age expires locally even when no new HTTP request succeeds or arrives.
        context, page, feed, errors, external = setup(browser, base_url, feed=Feed(age=358.5))
        page.wait_for_function("document.querySelector('#wind-state').textContent === 'PEARL STALE'", timeout=5000)
        assert feed.calls == 1
        assert page.locator('.wind-canvas').get_attribute('data-motion') == 'paused'
        page.screenshot(path=str(output / f'{engine}-stale.jpg'), type='jpeg', quality=90)
        context.close()
        for status, age in [('stale', 600), ('unavailable', 120), ('live', -600)]:
            context, page, feed, errors, external = setup(browser, base_url, feed=Feed(age=age, status=status))
            assert page.locator('.wind-canvas').get_attribute('data-motion') == 'paused'
            assert page.locator('#wind-state').inner_text() != 'PEARL LIVE'
            page.get_by_role('button', name='Explore', exact=True).click()
            assert page.locator('.wind-canvas').get_attribute('data-motion') == 'running'
            assert not errors, errors
            context.close()
        results.append({'local_age_expiry_stale_unavailable_future_and_explore': 'passed'})

        context, page, feed, errors, external = setup(browser, base_url, reduced=True)
        canvas = page.locator('.wind-canvas')
        assert canvas.get_attribute('data-motion') == 'reduced'
        first = canvas.evaluate('(c) => c.toDataURL()')
        page.wait_for_timeout(200)
        assert first == canvas.evaluate('(c) => c.toDataURL()')
        page.get_by_role('button', name='Explore', exact=True).click()
        page.locator('#direction-dial').focus()
        page.keyboard.press('ArrowRight')
        second = canvas.evaluate('(c) => c.toDataURL()')
        assert first != second
        page.wait_for_timeout(200)
        assert second == canvas.evaluate('(c) => c.toDataURL()')
        assert not errors, errors
        context.close()
        results.append({'reduced_motion_live_and_explore': 'passed'})
        browser.close()
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:5001')
    parser.add_argument('--output', type=Path, default=Path('/private/tmp/pearl-live-review'))
    parser.add_argument('--engine', choices=['chrome', 'webkit'], default='chrome')
    args = parser.parse_args()
    review(args.url, args.output, args.engine)
