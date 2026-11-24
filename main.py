# -*- coding: utf-8 -*-
# H&M 德扑值守 · Kivy 安卓版
# 与 v2.3.3 活动版同一套业务规则：9 宫格/多桌/买手/活动免费/酒水卡兑换/击杀/转赠/前三/历史/备份
import os, json, time, uuid, copy
from datetime import datetime
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.core.clipboard import Clipboard
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle, Line

BASE = os.path.dirname(os.path.abspath(__file__))
FONT = None
for p in ['/system/fonts/NotoSansCJK-Regular.ttc', '/system/fonts/NotoSansCJK-Regular.ttf',
          os.path.join(BASE, 'assets', 'wqy-microhei.ttc')]:
    if os.path.exists(p):
        FONT = p
        break
if FONT:
    try:
        LabelBase.register('Roboto', FONT)
    except Exception:
        pass

BG = (0.027, 0.07, 0.045, 1)
PANEL = (0.04, 0.15, 0.10, 1)
CARD = (0.055, 0.22, 0.15, 1)
CARD2 = (0.09, 0.32, 0.22, 1)
GOLD = (0.96, 0.82, 0.52, 1)
CREAM = (0.96, 0.90, 0.78, 1)
MUTED = (0.62, 0.68, 0.58, 1)
RED = (0.45, 0.06, 0.08, 1)
RED2 = (0.72, 0.12, 0.15, 1)
LINE = (0.42, 0.33, 0.16, 1)

SUITS = [('♠', False), ('♥', True), ('♦', True), ('♣', False)]


def uid():
    return uuid.uuid4().hex[:10]


def now():
    return int(time.time() * 1000)


def money(v):
    return '¥' + format(int(v or 0), ',')


def hhmm(ms):
    try:
        return datetime.fromtimestamp(ms / 1000).strftime('%H:%M')
    except Exception:
        return '--:--'


def date_str(ms):
    try:
        return datetime.fromtimestamp(ms / 1000).strftime('%m月%d日 %H:%M')
    except Exception:
        return ''


def L(text, size=10, color=CREAM, halign='left', shorten=False, **kw):
    lab = Label(text=text, font_size=sp(size), color=color, halign=halign,
                valign='middle', shorten=shorten, **kw)
    lab.bind(size=lambda *a: setattr(lab, 'text_size', (lab.width, None)))
    return lab


def B(text, cb, size=10, bg=CARD2, color=CREAM, height=dp(30), **kw):
    b = Button(text=text, font_size=sp(size), color=color, background_normal='',
               background_color=bg, size_hint_y=None, height=height, **kw)
    b.bind(on_release=lambda *a: cb())
    return b


def toast(msg):
    try:
        p = Popup(title='', content=Label(text=msg, font_size=sp(11), color=CREAM),
                  size_hint=(0.72, 0.12), auto_dismiss=True,
                  background_color=(0.05, 0.16, 0.11, 1))
        p.open()
        Clock.schedule_once(lambda dt: p.dismiss(), 1.4)
    except Exception:
        pass


# ---------------- data model ----------------
def new_entry(kind, hands, amount, cards, label, cards_used=0):
    return {'id': uid(), 'ts': now(), 'kind': kind, 'hands': hands, 'amount': amount,
            'cards': cards, 'cardsUsed': cards_used, 'label': label}


def new_player(name):
    return {'id': uid(), 'name': name.strip()[:12] or '客人', 'seatedAt': now(),
            'leftAt': None, 'outAt': None, 'outBy': None, 'outKill': None,
            'freeUsed': False, 'entries': []}


def new_seat(no):
    suit, red = SUITS[(no - 1) % 4]
    return {'no': no, 'suit': suit, 'red': red, 'player': None, 'history': [], 'newAt': 0}


def new_table(name):
    return {'id': uid(), 'name': name, 'createdAt': now(),
            'seats': [new_seat(i + 1) for i in range(9)], 'podium': [None, None, None]}


def new_session():
    t = new_table('1号桌')
    return {'id': uid(), 'startedAt': now(), 'endedAt': None, 'activeTableId': t['id'],
            'tables': [t], 'kills': [], 'gifts': [], 'podium': [None, None, None]}


def new_state():
    return {'version': 3, 'activityName': '手气王', 'freePromo': True, 'showSeatMeta': True,
            'sound': False, 'voice': False, 'announce30': False,
            'current': new_session(), 'archive': []}


def fix_entry(e):
    e = e or {}
    return {'id': e.get('id') or uid(), 'ts': int(e.get('ts') or now()),
            'kind': e.get('kind') or '1', 'hands': int(e.get('hands') or 0),
            'amount': int(e.get('amount') or 0), 'cards': int(e.get('cards') or 0),
            'cardsUsed': int(e.get('cardsUsed') or 0), 'label': str(e.get('label') or '')}


def fix_player(p):
    if not p:
        return None
    if not p.get('id'):
        p['id'] = uid()
    p['name'] = str(p.get('name') or '客人')[:12]
    p['seatedAt'] = int(p.get('seatedAt') or now())
    p['leftAt'] = int(p['leftAt']) if p.get('leftAt') else None
    p['outAt'] = int(p['outAt']) if p.get('outAt') else None
    p['outBy'] = p.get('outBy')
    p['outKill'] = p.get('outKill')
    p['freeUsed'] = bool(p.get('freeUsed'))
    p['entries'] = [fix_entry(e) for e in (p.get('entries') or []) if e]
    return p


def fix_seat(s, i):
    s = s or {}
    suit, red = SUITS[i % 4]
    return {'no': i + 1, 'suit': s.get('suit') or suit,
            'red': bool(s.get('red', red)), 'player': fix_player(s.get('player')),
            'history': [fix_player(x) for x in (s.get('history') or []) if x],
            'newAt': int(s.get('newAt') or 0)}


def fix_table(t, i):
    t = t or {}
    table = {'id': t.get('id') or uid(), 'name': str(t.get('name') or (str(i + 1) + '号桌'))[:12],
             'createdAt': int(t.get('createdAt') or now()), 'seats': [],
             'podium': [None, None, None]}
    old = t.get('seats') or []
    for j in range(9):
        table['seats'].append(fix_seat(old[j] if j < len(old) else None, j))
    p = t.get('podium') or []
    for j in range(3):
        if j < len(p) and isinstance(p[j], str):
            table['podium'][j] = p[j]
    return table


def normalize_session(s):
    if not isinstance(s, dict):
        return new_session()
    if not isinstance(s.get('tables'), list) or not s['tables']:
        s['tables'] = [new_table('1号桌')]
    s['tables'] = [fix_table(t, i) for i, t in enumerate(s['tables'][:4])]
    ids = [t['id'] for t in s['tables']]
    if s.get('activeTableId') not in ids:
        s['activeTableId'] = ids[0]
    s['id'] = s.get('id') or uid()
    s['startedAt'] = int(s.get('startedAt') or now())
    s['endedAt'] = int(s['endedAt']) if s.get('endedAt') else None
    kills = []
    for k in (s.get('kills') or []):
        if not k or not k.get('winnerId') or not k.get('loserId'):
            continue
        if k['winnerId'] == k['loserId']:
            continue
        kills.append({'id': k.get('id') or uid(), 'ts': int(k.get('ts') or now()),
                      'tableId': k.get('tableId') or '', 'winnerId': str(k['winnerId']),
                      'loserId': str(k['loserId']), 'card': k.get('card') is not False})
    s['kills'] = kills
    gifts = []
    for g in (s.get('gifts') or []):
        if not g or not g.get('fromId') or not g.get('toId') or g['fromId'] == g['toId']:
            continue
        gifts.append({'id': g.get('id') or uid(), 'ts': int(g.get('ts') or now()),
                      'fromId': str(g['fromId']), 'toId': str(g['toId']),
                      'amount': max(1, int(g.get('amount') or 1)),
                      'fromTableId': g.get('fromTableId') or '',
                      'toTableId': g.get('toTableId') or ''})
    s['gifts'] = gifts
    p = s.get('podium') or []
    s['podium'] = [p[i] if i < len(p) and isinstance(p[i], str) else None for i in range(3)]
    return s


def normalize(s):
    if not isinstance(s, dict):
        return new_state()
    if not isinstance(s.get('activityName'), str) or not s['activityName'].strip():
        s['activityName'] = '手气王'
    if s['activityName'] == '手机王':
        s['activityName'] = '手气王'
    s['freePromo'] = bool(s.get('freePromo', True))
    s['showSeatMeta'] = bool(s.get('showSeatMeta', True))
    s['sound'] = False
    s['voice'] = False
    s['announce30'] = False
    s['current'] = normalize_session(s.get('current'))
    if not isinstance(s.get('archive'), list):
        s['archive'] = []
    s['archive'] = [normalize_session(x) for x in s['archive'] if isinstance(x, dict)][:300]
    s['version'] = 3
    return s


def entry_totals(p):
    hands = amount = cards = used = 0
    for e in p.get('entries', []):
        hands += int(e.get('hands') or 0)
        amount += int(e.get('amount') or 0)
        cards += int(e.get('cards') or 0)
        used += int(e.get('cardsUsed') or 0)
    return {'hands': hands, 'amount': amount, 'cards': cards, 'cardsUsed': used}


def free_count(p):
    return len([e for e in p.get('entries', []) if e.get('kind') == 'free'])


def card_ex_count(p):
    return len([e for e in p.get('entries', []) if e.get('kind') in ('card5', 'card10')])


def kill_stats(p, session):
    t = entry_totals(p)
    ks = 0
    won = given = 0
    for k in session.get('kills', []):
        card = k.get('card') is not False
        if k.get('winnerId') == p['id']:
            ks += 1
            if card:
                won += 1
        if k.get('loserId') == p['id'] and card:
            given += 1
    gin = sum(g['amount'] for g in session.get('gifts', []) if g.get('toId') == p['id'])
    gout = sum(g['amount'] for g in session.get('gifts', []) if g.get('fromId') == p['id'])
    return {'hands': t['hands'], 'amount': t['amount'], 'cards': t['cards'],
            'cardsUsed': t['cardsUsed'], 'kills': ks, 'won': won, 'given': given,
            'giftIn': gin, 'giftOut': gout,
            'balance': t['hands'] + won + gin - given - gout}


def players_of(session):
    out = []
    for t in session.get('tables', []):
        for s in t.get('seats', []):
            p = s.get('player')
            if p:
                out.append({'p': p, 'table': t, 'tableId': t['id'], 'tableName': t['name'],
                            'seat': s, 'seatNo': s['no'], 'live': not p.get('outAt') and not p.get('leftAt')})
    return out


def find_player(session, pid):
    for x in players_of(session):
        if x['p']['id'] == pid:
            return x
    return None


def find_table(session, tid):
    for t in session.get('tables', []):
        if t['id'] == tid:
            return t
    return None


def table_totals(t):
    ps = []
    hands = amount = cards = used = 0
    for s in t.get('seats', []):
        p = s.get('player')
        if not p:
            continue
        e = entry_totals(p)
        hands += e['hands']; amount += e['amount']; cards += e['cards']; used += e['cardsUsed']
        ps.append({'p': p, 'seat': s, 'live': not p.get('outAt') and not p.get('leftAt')})
    return {'players': ps, 'hands': hands, 'amount': amount, 'cards': cards, 'cardsUsed': used}


def session_totals(s):
    ps = []
    hands = amount = cards = used = 0
    for t in s.get('tables', []):
        tt = table_totals(t)
        ps += tt['players']
        hands += tt['hands']; amount += tt['amount']; cards += tt['cards']; used += tt['cardsUsed']
    return {'players': ps, 'live': len([x for x in ps if x['live']]),
            'hands': hands, 'amount': amount, 'cards': cards, 'cardsUsed': used}


class SeatCard(BoxLayout):
    def __init__(self, root, table, seat, **kw):
        super().__init__(orientation='vertical', padding=dp(4), spacing=dp(1),
                         size_hint=(1, 1), **kw)
        self.root = root
        self.table = table
        self.seat = seat
        self._down = False
        self._quick = None
        p = seat.get('player')
        out = bool(p and p.get('outAt'))
        bg = (0.18, 0.06, 0.07, 1) if out else (0.055, 0.22, 0.15, 1)
        with self.canvas.before:
            Color(*bg)
            self.bg = RoundedRectangle(radius=[dp(7)])
            Color(*(RED2 if out else LINE))
            self.border = Line(rounded_rectangle=(0, 0, 0, 0, dp(7)), width=dp(1))
        self.bind(pos=self._upd, size=self._upd)
        if not p:
            top = BoxLayout(size_hint_y=None, height=dp(16))
            top.add_widget(L('%02d' % seat['no'], 7, GOLD, halign='center'))
            top.add_widget(L(seat['suit'], 8, MUTED, halign='center'))
            self.add_widget(top)
            self.add_widget(L('＋', 22, GOLD, halign='center'))
            self.add_widget(L('空位', 9, CREAM, halign='center'))
            self.add_widget(L('点此入座', 7, MUTED, halign='center'))
            return
        t = entry_totals(p)
        ks = kill_stats(p, root.state['current'])
        top = BoxLayout(size_hint_y=None, height=dp(15), spacing=dp(1))
        top.add_widget(L('%02d' % seat['no'], 7, GOLD, halign='center'))
        if p['id'] in (table.get('podium') or []):
            top.add_widget(L('♛', 7, GOLD, halign='center'))
        top.add_widget(L(seat['suit'], 8, (1, 0.4, 0.4, 1) if seat['red'] else CREAM, halign='center'))
        self.add_widget(top)
        name = p['name'] + (' OUT' if out else '')
        self.add_widget(L(name, 9, CREAM, shorten=True))
        self.add_widget(L('%d手' % t['hands'], 17, GOLD, halign='left'))
        if root.state.get('showSeatMeta', True):
            meta = '%s  酒%d  杀%d' % (money(t['amount']), t['cards'], ks['balance'])
            self.add_widget(L(meta, 6.5, MUTED, shorten=True))
        idx = len(seat.get('history') or []) + 1
        self.add_widget(L('第%d位' % idx, 6, MUTED))
        self._quick = BoxLayout(size_hint_y=None, height=dp(25), spacing=dp(2))
        self._quick.add_widget(B('+1手', lambda: root.add_hands(table, seat, '1'), size=8, height=dp(23)))
        self._quick.add_widget(B('+2手', lambda: root.add_hands(table, seat, '2'), size=8, height=dp(23)))
        self.add_widget(self._quick)

    def _upd(self, *a):
        self.bg.pos = self.pos
        self.bg.size = self.size
        self.border.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(7))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._down = not (self._quick and self._quick.collide_point(*touch.pos))
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self._down and self.collide_point(*touch.pos):
            if not (self._quick and self._quick.collide_point(*touch.pos)):
                self.root.tap_seat(self.table, self.seat)
        self._down = False
        return super().on_touch_up(touch)


class Root(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(orientation='vertical', padding=dp(4), spacing=dp(2), **kw)
        self.app = app
        self.state = app.state
        self._undo = []
        top = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(2))
        top.add_widget(L('H&M 德扑值守', 17, GOLD))
        for txt, cb in [('榜', self.open_summary), ('史', self.open_history), ('设', self.open_settings)]:
            top.add_widget(B(txt, cb, size=9, height=dp(30), size_hint_x=None, width=dp(34)))
        self.add_widget(top)
        self.sub = L('', 8, MUTED)
        self.add_widget(self.sub)
        self.ticker = L('', 8, GOLD)
        self.add_widget(self.ticker)
        self.tabs = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(3))
        self.add_widget(self.tabs)
        self.board = GridLayout(cols=3, spacing=dp(4), size_hint_y=1)
        self.add_widget(self.board)
        self.stats = BoxLayout(size_hint_y=None, height=dp(36))
        self.add_widget(self.stats)
        acts = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(3))
        acts.add_widget(B('撤销', self.undo, size=9))
        acts.add_widget(B('本场明细', self.open_summary, size=9))
        acts.add_widget(B('击杀', self.open_kill, size=9, bg=RED2))
        acts.add_widget(B('交班', self.end_session, size=9, bg=(0.72, 0.55, 0.2, 1), color=(0.1, 0.07, 0.03, 1)))
        self.add_widget(acts)
        self.refresh()

    def refresh(self):
        self.state = self.app.state
        s = self.state['current']
        t = find_table(s, s['activeTableId']) or s['tables'][0]
        self.sub.text = '%s · %s · %s 开场' % (t['name'], date_str(s['startedAt']), '等待开台' if not session_totals(s)['players'] else '')
        self.ticker.text = ('活动免费一手（%s） · ' % self.state['activityName'] if self.state['freePromo'] else '') + '1手 ¥48（送1卡） · 2手 ¥98（送2卡）'
        self.tabs.clear_widgets()
        for tb in s['tables']:
            b = B(tb['name'], lambda tid=tb['id']: self.switch_table(tid), size=8, height=dp(30))
            if tb['id'] == t['id']:
                b.background_color = (0.6, 0.45, 0.15, 1)
            self.tabs.add_widget(b)
        if len(s['tables']) < 4:
            self.tabs.add_widget(B('＋开桌', self.open_table_manager, size=8, height=dp(30)))
        self.board.clear_widgets()
        for seat in t['seats']:
            self.board.add_widget(SeatCard(self, t, seat))
        st = session_totals(s)
        self.stats.clear_widgets()
        for txt, val, color in [('存活', str(st['live']), CREAM), ('全场手数', str(st['hands']), CREAM),
                                ('流水', money(st['amount']), GOLD), ('发卡', str(st['cards']), CREAM),
                                ('收卡', str(st['cardsUsed']), CREAM)]:
            box = BoxLayout(orientation='vertical')
            box.add_widget(L(val, 11, color, halign='center'))
            box.add_widget(L(txt, 6.5, MUTED, halign='center'))
            self.stats.add_widget(box)

    def push_undo(self):
        try:
            self._undo.append(copy.deepcopy(self.state))
            self._undo = self._undo[-8:]
        except Exception:
            pass

    def undo(self):
        if not self._undo:
            toast('没有可撤销的操作')
            return
        self.app.state = self._undo.pop()
        self.save()
        toast('已撤销')

    def save(self):
        self.app.save()
        self.refresh()

    def tap_seat(self, table, seat):
        if seat.get('player'):
            self.open_player(table, seat)
        else:
            self.open_add(table, seat)

    def add_player(self, table, seat, name, free):
        self.push_undo()
        p = new_player(name)
        if seat.get('player'):
            seat['history'].append(seat['player'])
        seat['player'] = p
        seat['newAt'] = now()
        if free and self.state['freePromo'] and p['freeUsed'] is False:
            p['freeUsed'] = True
            p['entries'].append(new_entry('free', 1, 0, 0, self.state['activityName'] + '活动免费一手'))
        self.save()

    def add_hands(self, table, seat, kind):
        p = seat.get('player')
        if not p:
            return
        self.push_undo()
        if kind == '1':
            p['entries'].append(new_entry('1', 1, 48, 1, '+1手'))
        elif kind == '2':
            p['entries'].append(new_entry('2', 2, 98, 2, '+2手'))
        elif kind == 'free':
            if not self.state['freePromo']:
                toast('活动免费已关闭')
                return
            if p.get('freeUsed') or free_count(p) > 0:
                toast('这位客人已领过')
                return
            p['freeUsed'] = True
            p['entries'].append(new_entry('free', 1, 0, 0, self.state['activityName'] + '活动免费一手'))
        elif kind == 'card5':
            p['entries'].append(new_entry('card5', 1, 0, 0, '5卡换1手（48）', 5))
        elif kind == 'card10':
            p['entries'].append(new_entry('card10', 2, 0, 0, '10卡换2手（98）', 10))
        self.save()

    def delete_entry(self, p, eid):
        self.push_undo()
        p['entries'] = [e for e in p.get('entries', []) if e.get('id') != eid]
        self.save()

    def rename_player(self, p, name):
        self.push_undo()
        p['name'] = (name or '').strip()[:12] or p['name']
        self.save()

    def leave_player(self, table, seat):
        self.push_undo()
        p = seat.get('player')
        if p:
            p['leftAt'] = now()
            seat['history'].append(p)
            seat['player'] = None
            seat['newAt'] = 0
        self.save()

    def open_add(self, table, seat):
        box = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(8))
        name = TextInput(hint_text='玩家名字 / 昵称', multiline=False, font_size=sp(14))
        box.add_widget(L('安排入座 · %s 座位 %d' % (table['name'], seat['no']), 13, GOLD))
        box.add_widget(name)
        frow = BoxLayout(size_hint_y=None, height=dp(30))
        frow.add_widget(L('送活动免费一手', 10, CREAM))
        chk = CheckBox(active=False, size_hint_x=None, width=dp(40))
        frow.add_widget(chk)
        box.add_widget(frow)
        box.add_widget(L('每位客人限一次；没有活动就不勾', 7, MUTED))
        btn = Button(text='坐下开台', font_size=sp(12), background_normal='',
                     background_color=(0.6, 0.45, 0.15, 1), color=(0.1, 0.07, 0.03, 1))
        box.add_widget(btn)
        p = Popup(title='入座', content=box, size_hint=(0.9, 0.55), title_color=GOLD,
                  separator_color=GOLD, background_color=(0.04, 0.12, 0.08, 1))
        def go(*a):
            self.add_player(table, seat, name.text, chk.active)
            p.dismiss()
            toast('已入座')
        btn.bind(on_release=go)
        p.open()

    def open_player(self, table, seat):
        p = seat.get('player')
        if not p:
            return
        t = entry_totals(p)
        ks = kill_stats(p, self.state['current'])
        box = BoxLayout(orientation='vertical', spacing=dp(3), padding=dp(6))
        box.add_widget(L('%s · %s %d号位' % (p['name'], table['name'], seat['no']), 14, GOLD))
        box.add_widget(L('%d手 · %s · 发%d 收%d · 击杀卡%d' % (t['hands'], money(t['amount']), t['cards'], t['cardsUsed'], ks['balance']), 9, CREAM))
        g = GridLayout(cols=2, spacing=dp(3), size_hint_y=None, height=dp(96))
        for txt, cb in [('+1手 ¥48', lambda: self.add_hands(table, seat, '1')),
                        ('+2手 ¥98', lambda: self.add_hands(table, seat, '2')),
                        ('活动免费', lambda: self.add_hands(table, seat, 'free')),
                        ('5卡换1手', lambda: self.add_hands(table, seat, 'card5')),
                        ('10卡换2手', lambda: self.add_hands(table, seat, 'card10')),
                        ('恢复存活', lambda: self.revive(p))]:
            g.add_widget(B(txt, cb, size=9, height=dp(28)))
        box.add_widget(g)
        row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(2))
        row.add_widget(B('击杀', lambda: self.open_kill(), size=9, bg=RED2))
        row.add_widget(B('赠送', lambda: self.open_gift(p), size=9))
        row.add_widget(B('改名', lambda: self.open_rename(p), size=9))
        row.add_widget(B('下桌', lambda: self.leave_player(table, seat), size=9))
        box.add_widget(row)
        sv = ScrollView()
        el = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(1))
        el.bind(minimum_height=el.setter('height'))
        for e in reversed(p.get('entries', [])):
            r = BoxLayout(size_hint_y=None, height=dp(26), spacing=dp(2))
            r.add_widget(L('%s %s' % (hhmm(e.get('ts')), e.get('label', '')), 8, CREAM, shorten=True))
            r.add_widget(B('✕', lambda eid=e['id']: (self.delete_entry(p, eid), pp.dismiss()), size=8,
                           height=dp(24), size_hint_x=None, width=dp(28), bg=RED2))
            el.add_widget(r)
        sv.add_widget(el)
        box.add_widget(sv)
        box.add_widget(B('关闭', lambda: pp.dismiss(), size=10))
        pp = Popup(title='买手单', content=box, size_hint=(0.94, 0.86), title_color=GOLD,
                   separator_color=GOLD, background_color=(0.04, 0.12, 0.08, 1))
        pp.open()

    def open_rename(self, p):
        box = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(8))
        ti = TextInput(text=p['name'], multiline=False, font_size=sp(14))
        box.add_widget(ti)
        b = Button(text='保存', size_hint_y=None, height=dp(34), background_normal='',
                   background_color=(0.6, 0.45, 0.15, 1))
        box.add_widget(b)
        po = Popup(title='改名', content=box, size_hint=(0.8, 0.3), title_color=GOLD,
                   separator_color=GOLD, background_color=(0.04, 0.12, 0.08, 1))
        def go(*a):
            self.rename_player(p, ti.text)
            po.dismiss()
        b.bind(on_release=go)
        po.open()

    def open_kill(self):
        win = {'id': None}
        lose = {'id': None}
        box = BoxLayout(orientation='vertical', spacing=dp(4), padding=dp(6))
        box.add_widget(L('记录击杀 · 先点赢家，再点输家', 10, GOLD))
        players = players_of(self.state['current'])
        grids = []
        for role, d in [('赢家（收卡）', win), ('输家（淘汰）', lose)]:
            box.add_widget(L(role, 8, GOLD))
            g = GridLayout(cols=3, spacing=dp(2), size_hint_y=None, height=dp(120))
            for x in players:
                b = B(x['p']['name'], lambda x=x: self._pick_kill(win, lose, x['p']['id'], x['p']['name']), size=8, height=dp(30))
                g.add_widget(b)
            grids.append(g)
            box.add_widget(g)
        card = CheckBox(active=True, size_hint_x=None, width=dp(40))
        cr = BoxLayout(size_hint_y=None, height=dp(28))
        cr.add_widget(L('有卡（输家给赢家1张）', 9, CREAM))
        cr.add_widget(card)
        box.add_widget(cr)
        btn = Button(text='确认淘汰', size_hint_y=None, height=dp(36), background_normal='',
                     background_color=(0.72, 0.12, 0.15, 1))
        box.add_widget(btn)
        po = Popup(title='击杀', content=box, size_hint=(0.94, 0.8), title_color=GOLD,
                   separator_color=GOLD, background_color=(0.04, 0.12, 0.08, 1))
        self._kill_popup = po
        def go(*a):
            if not win['id'] or not lose['id'] or win['id'] == lose['id']:
                toast('赢家和输家都要选，且不能同一人')
                return
            self.push_undo()
            self.state['current']['kills'].append({'id': uid(), 'ts': now(),
                'tableId': self.active_table()['id'], 'winnerId': win['id'],
                'loserId': lose['id'], 'card': card.active})
            x = find_player(self.state['current'], lose['id'])
            if x:
                x['p']['outAt'] = now(); x['p']['outBy'] = win['id']; x['p']['outKill'] = 'x'
            self.save(); po.dismiss(); toast('已记录击杀')
        btn.bind(on_release=go)
        po.open()

    def _pick_kill(self, win, lose, pid, name):
        if win['id'] is None:
            win['id'] = pid; win['name'] = name
            toast('赢家：' + name)
        else:
            lose['id'] = pid; lose['name'] = name
            toast('输家：' + name)

    def revive(self, p):
        self.push_undo()
        p['outAt'] = None; p['outBy'] = None; p['outKill'] = None
        self.save()

    def open_gift(self, p):
        box = BoxLayout(orientation='vertical', spacing=dp(4), padding=dp(6))
        ks = kill_stats(p, self.state['current'])
        box.add_widget(L('%s 当前击杀卡 %d 张' % (p['name'], ks['balance']), 10, GOLD))
        to = {'id': None}
        g = GridLayout(cols=2, spacing=dp(2), size_hint_y=None, height=dp(120))
        for x in players_of(self.state['current']):
            if x['p']['id'] == p['id']:
                continue
            g.add_widget(B(x['p']['name'], lambda x=x: to.update({'id': x['p']['id']}) or toast('接收人：' + x['p']['name']), size=8, height=dp(30)))
        box.add_widget(g)
        amt = TextInput(text='1', input_filter='int', multiline=False, size_hint_y=None,
                        height=dp(32), font_size=sp(14))
        box.add_widget(amt)
        btn = Button(text='确认赠送', size_hint_y=None, height=dp(34), background_normal='',
                     background_color=(0.6, 0.45, 0.15, 1))
        box.add_widget(btn)
        po = Popup(title='赠送击杀卡', content=box, size_hint=(0.92, 0.65), title_color=GOLD,
                   separator_color=GOLD, background_color=(0.04, 0.12, 0.08, 1))
        def go(*a):
            if not to['id']:
                toast('先选接收人')
                return
            try:
                n = max(1, int(amt.text or 1))
            except Exception:
                n = 1
            if n > ks['balance']:
                toast('最多只能送 %d 张' % ks['balance'])
                return
            self.push_undo()
            self.state['current']['gifts'].append({'id': uid(), 'ts': now(),
                'fromId': p['id'], 'toId': to['id'], 'amount': n,
                'fromTableId': '', 'toTableId': ''})
            self.save(); po.dismiss(); toast('已赠送 %d 张' % n)
        btn.bind(on_release=go)
        po.open()

    def active_table(self):
        s = self.state['current']
        return find_table(s, s['activeTableId']) or s['tables'][0]

    def switch_table(self, tid):
        self.state['current']['activeTableId'] = tid
        self.save()

    def open_table_manager(self):
        box = BoxLayout(orientation='vertical', spacing=dp(4), padding=dp(6))
        box.add_widget(L('当前桌子：' + self.active_table()['name'], 10, GOLD))
        ti = TextInput(text=self.active_table()['name'], multiline=False, size_hint_y=None, height=dp(32))
        box.add_widget(ti)
        row = BoxLayout(size_hint_y=None, height=dp(30), spacing=dp(2))
        row.add_widget(B('改名', lambda: self.rename_table(ti.text), size=9))
        row.add_widget(B('＋开桌', self.new_table, size=9))
        row.add_widget(B('关闭空桌', self.close_table, size=9))
        box.add_widget(row)
        box.add_widget(B('关闭', lambda: po.dismiss(), size=9))
        po = Popup(title='桌台管理', content=box, size_hint=(0.85, 0.42), title_color=GOLD,
                   separator_color=GOLD, background_color=(0.04, 0.12, 0.08, 1))
        po.open()

    def rename_table(self, name):
        self.push_undo()
        self.active_table()['name'] = (name or '').strip()[:12] or self.active_table()['name']
        self.save()

    def new_table(self):
        s = self.state['current']
        if len(s['tables']) >= 4:
            toast('最多4桌')
            return
        self.push_undo()
        t = new_table(str(len(s['tables']) + 1) + '号桌')
        s['tables'].append(t)
        s['activeTableId'] = t['id']
        self.save()

    def close_table(self):
        s = self.state['current']
        if len(s['tables']) <= 1:
            toast('至少留1桌')
            return
        t = self.active_table()
        if any(x['player'] for x in t['seats']):
            toast('这桌还有人，先下桌')
            return
        self.push_undo()
        s['tables'] = [x for x in s['tables'] if x['id'] != t['id']]
        s['activeTableId'] = s['tables'][0]['id']
        self.save()

    def summary_text(self, session=None, plain=False):
        s = session or self.state['current']
        st = session_totals(s)
        lines = []
        lines.append('H&M 德扑值守 · ' + self.state['activityName'])
        lines.append('%s · 本场 %d 人次 · 存活 %d' % (date_str(s['startedAt']), len(st['players']), st['live']))
        lines.append('总手数 %d · 总流水 %s · 发卡 %d · 收卡 %d' % (st['hands'], money(st['amount']), st['cards'], st['cardsUsed']))
        free = sum(free_count(x['p']) for x in st['players'])
        if free:
            lines.append('活动免费手 %d 手（%s）' % (free, self.state['activityName']))
        for t in s['tables']:
            tt = table_totals(t)
            lines.append('')
            lines.append('【%s】%d 存活 · %d手 · %s' % (t['name'], len([x for x in tt['players'] if x['live']]), tt['hands'], money(tt['amount'])))
            for x in tt['players']:
                p = x['p']
                ks = kill_stats(p, s)
                lines.append('  %s %s %d手 %s 发%d 收%d 卡%d%s' % (
                    p['name'], '已淘汰' if p.get('outAt') else '在座', ks['hands'], money(ks['amount']),
                    ks['cards'], ks['cardsUsed'], ks['balance'], ' 冠军' if p['id'] == (t.get('podium') or [None])[0] else ''))
        if s.get('kills'):
            lines.append('')
            lines.append('击杀记录：')
            for k in s['kills']:
                w = find_player(s, k['winnerId']); l = find_player(s, k['loserId'])
                lines.append('  %s 淘汰 %s%s' % (w['p']['name'] if w else '?', l['p']['name'] if l else '?', '' if k.get('card') else '（无卡）'))
        if s.get('gifts'):
            lines.append('')
            lines.append('转赠记录：')
            for g in s['gifts']:
                f = find_player(s, g['fromId']); t = find_player(s, g['toId'])
                lines.append('  %s 赠给 %s %d张' % (f['p']['name'] if f else '?', t['p']['name'] if t else '?', g['amount']))
        if s.get('podium') and any(s['podium']):
            lines.append('')
            lines.append('本场前三：' + ' / '.join([find_player(s, x)['p']['name'] if x and find_player(s, x) else '—' for x in s['podium']]))
        if plain:
            return '\n'.join(lines)
        return '\n'.join(lines).replace('&', '&amp;')

    def open_summary(self):
        text = self.summary_text()
        box = BoxLayout(orientation='vertical', spacing=dp(3), padding=dp(5))
        lab = Label(text='[b]本场明细[/b]\n' + text, markup=True, font_size=sp(10),
                    color=CREAM, halign='left', valign='top', size_hint_y=None)
        lab.bind(width=lambda *a: setattr(lab, 'text_size', (lab.width, None)))
        lab.bind(texture_size=lambda *a: setattr(lab, 'height', lab.texture_size[1]))
        sv = ScrollView()
        sv.add_widget(lab)
        box.add_widget(sv)
        row = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(2))
        row.add_widget(B('复制文本', lambda: (Clipboard.copy(self.summary_text(plain=True)), toast('已复制')), size=9))
        row.add_widget(B('前三', self.open_podium, size=9))
        row.add_widget(B('导出备份', self.export_state, size=9))
        row.add_widget(B('关闭', lambda: po.dismiss(), size=9))
        box.add_widget(row)
        po = Popup(title='本场明细', content=box, size_hint=(0.96, 0.9), title_color=GOLD,
                   separator_color=GOLD, background_color=(0.04, 0.12, 0.08, 1))
        po.open()

    def open_podium(self):
        table = self.active_table()
        ps = [x for x in players_of(self.state['current']) if x['tableId'] == table['id']]
        box = BoxLayout(orientation='vertical', spacing=dp(3), padding=dp(6))
        box.add_widget(L('点名字循环：第1名 → 第2名 → 第3名 → 取消', 8, MUTED))
        grid = GridLayout(cols=2, spacing=dp(2), size_hint_y=None, height=dp(150))
        place = {}
        btns = {}
        names = {x['p']['id']: x['p']['name'] for x in ps}

        def cycle(pid):
            n = (place.get(pid, 0) + 1) % 4
            if n == 0:
                place.pop(pid, None)
            else:
                for k, v in list(place.items()):
                    if v == n:
                        place.pop(k, None)
                place[pid] = n
            for pid2, b in btns.items():
                if pid2 in place:
                    b.text = '%s  第%d' % (names[pid2], place[pid2])
                    b.background_color = (0.6, 0.45, 0.15, 1)
                else:
                    b.text = names[pid2]
                    b.background_color = CARD2

        for x in ps:
            b = B(x['p']['name'], lambda pid=x['p']['id']: cycle(pid), size=8, height=dp(28))
            btns[x['p']['id']] = b
            grid.add_widget(b)
        if not ps:
            grid.add_widget(L('这桌还没有客人', 9, MUTED, halign='center'))
        box.add_widget(grid)
        btn = Button(text='保存前三', size_hint_y=None, height=dp(34), background_normal='',
                     background_color=(0.6, 0.45, 0.15, 1))
        box.add_widget(btn)
        po = Popup(title='本桌前三', content=box, size_hint=(0.88, 0.55), title_color=GOLD,
                   separator_color=GOLD, background_color=(0.04, 0.12, 0.08, 1))
        def save(*a):
            arr = [None, None, None]
            for pid, n in place.items():
                if 1 <= n <= 3:
                    arr[n - 1] = pid
            table['podium'] = arr
            self.save(); po.dismiss(); toast('前三已更新')
        btn.bind(on_release=save)
        po.open()

    def open_history(self):
        box = BoxLayout(orientation='vertical', spacing=dp(3), padding=dp(5))
        sv = ScrollView()
        el = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(2))
        el.bind(minimum_height=el.setter('height'))
        for i, s in enumerate(self.state.get('archive', [])):
            st = session_totals(s)
            el.add_widget(B('%s · %d人次 · %s' % (date_str(s['startedAt']), len(st['players']), money(st['amount'])),
                            lambda s=s: self.open_archive(s), size=8, height=dp(32)))
        if not self.state.get('archive'):
            el.add_widget(L('还没有历史场次', 10, MUTED, halign='center'))
        sv.add_widget(el)
        box.add_widget(sv)
        box.add_widget(B('关闭', lambda: po.dismiss(), size=9))
        po = Popup(title='历史场次', content=box, size_hint=(0.94, 0.8), title_color=GOLD,
                   separator_color=GOLD, background_color=(0.04, 0.12, 0.08, 1))
        po.open()

    def open_archive(self, s):
        box = BoxLayout(orientation='vertical', spacing=dp(3), padding=dp(5))
        lab = Label(text=self.summary_text(s), font_size=sp(9), color=CREAM, halign='left', valign='top', size_hint_y=None)
        lab.bind(width=lambda *a: setattr(lab, 'text_size', (lab.width, None)))
        lab.bind(texture_size=lambda *a: setattr(lab, 'height', lab.texture_size[1]))
        sv = ScrollView(); sv.add_widget(lab); box.add_widget(sv)
        box.add_widget(B('关闭', lambda: po.dismiss(), size=9))
        po = Popup(title='历史明细', content=box, size_hint=(0.96, 0.9), title_color=GOLD,
                   separator_color=GOLD, background_color=(0.04, 0.12, 0.08, 1))
        po.open()

    def open_settings(self):
        box = BoxLayout(orientation='vertical', spacing=dp(4), padding=dp(6))
        ti = TextInput(text=self.state['activityName'], multiline=False, size_hint_y=None, height=dp(32))
        box.add_widget(L('活动名称（如 手气王）', 9, GOLD))
        box.add_widget(ti)
        fr = BoxLayout(size_hint_y=None, height=dp(30))
        fr.add_widget(L('活动免费一手', 10, CREAM))
        fc = CheckBox(active=self.state['freePromo'], size_hint_x=None, width=dp(40))
        fr.add_widget(fc); box.add_widget(fr)
        mr = BoxLayout(size_hint_y=None, height=dp(30))
        mr.add_widget(L('小屏显示座位数据', 10, CREAM))
        mc = CheckBox(active=self.state['showSeatMeta'], size_hint_x=None, width=dp(40))
        mr.add_widget(mc); box.add_widget(mr)
        row = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(2))
        row.add_widget(B('导出备份', self.export_state, size=9))
        row.add_widget(B('导入备份', self.import_state, size=9))
        row.add_widget(B('保存', lambda: self.save_settings(ti.text, fc.active, mc.active), size=9))
        box.add_widget(row)
        box.add_widget(B('关闭', lambda: po.dismiss(), size=9))
        po = Popup(title='设置', content=box, size_hint=(0.9, 0.55), title_color=GOLD,
                   separator_color=GOLD, background_color=(0.04, 0.12, 0.08, 1))
        po.open()

    def save_settings(self, name, free, meta):
        self.push_undo()
        self.state['activityName'] = (name or '').strip()[:16] or '手气王'
        self.state['freePromo'] = bool(free)
        self.state['showSeatMeta'] = bool(meta)
        self.save()
        toast('设置已保存')

    def export_state(self):
        try:
            path = os.path.join(self.app.user_data_dir, 'HM德扑值守备份-%s.json' % datetime.now().strftime('%Y%m%d-%H%M%S'))
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=1)
            try:
                from plyer import share
                share.share(filepath=path, title='H&M 德扑值守备份')
            except Exception:
                Clipboard.copy(json.dumps(self.state, ensure_ascii=False))
            toast('备份已生成：' + path)
        except Exception as e:
            toast('导出失败：' + str(e))

    def import_state(self):
        try:
            from plyer import filechooser
            paths = filechooser.open_file(filters=[('JSON', '*.json')])
            if not paths:
                return
            with open(paths[0], 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.app.state = normalize(data)
            self.save()
            toast('已导入备份')
        except Exception as e:
            toast('导入失败：' + str(e))

    def end_session(self):
        s = self.state['current']
        if not session_totals(s)['players']:
            toast('本场还没有客人')
            return
        self.push_undo()
        s['endedAt'] = now()
        self.state['archive'].insert(0, copy.deepcopy(s))
        self.state['archive'] = self.state['archive'][:300]
        self.state['current'] = new_session()
        self.save()
        toast('本场已归档，开新场')


class PokerApp(App):
    def build(self):
        Window.clearcolor = BG
        Window.softinput_mode = 'below_target'
        self.state = self.load_state()
        self.root = Root(self)
        return self.root

    def state_path(self):
        base = self.user_data_dir
        try:
            os.makedirs(base, exist_ok=True)
        except Exception:
            pass
        return os.path.join(base, 'state.json')

    def load_state(self):
        try:
            with open(self.state_path(), 'r', encoding='utf-8') as f:
                return normalize(json.load(f))
        except Exception:
            return new_state()

    def save(self):
        try:
            with open(self.state_path(), 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=1)
        except Exception:
            pass

    def on_stop(self):
        self.save()


if __name__ == '__main__':
    PokerApp().run()
