import {
	combineRgb,
	InstanceBase,
	InstanceStatus,
	runEntrypoint,
} from '@companion-module/base'
import * as config from './config.js'

const GROUP_CHOICES = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'Q'].map((group) => ({
	id: group,
	label: group,
}))

const PLAYER_COMMAND_CHOICES = [
	{ id: 'pause', label: 'Pause' },
	{ id: 'resume', label: 'Resume' },
	{ id: 'stop', label: 'Stop' },
	{ id: 'forcestop', label: 'Force Stop' },
	{ id: 'playnext', label: 'Play Next' },
	{ id: 'rapidfire', label: 'Rapid Fire' },
	{ id: 'playselected', label: 'Play Selected' },
	{ id: 'playselectedpause', label: 'Play Selected / Pause' },
	{ id: 'mute', label: 'Mute Toggle' },
	{ id: 'talk/enable', label: 'Talk Enable' },
	{ id: 'talk/disable', label: 'Talk Disable' },
	{ id: 'talk/toggle', label: 'Talk Toggle' },
	{ id: 'playlist/enable', label: 'Playlist Enable' },
	{ id: 'playlist/disable', label: 'Playlist Disable' },
	{ id: 'playlist/toggle', label: 'Playlist Toggle' },
	{ id: 'playlist/shuffle/enable', label: 'Shuffle Enable' },
	{ id: 'playlist/shuffle/disable', label: 'Shuffle Disable' },
	{ id: 'playlist/shuffle/toggle', label: 'Shuffle Toggle' },
	{ id: 'multiplay/enable', label: 'Multi-play Enable' },
	{ id: 'multiplay/disable', label: 'Multi-play Disable' },
	{ id: 'multiplay/toggle', label: 'Multi-play Toggle' },
	{ id: 'fadein/enable', label: 'Fade In Enable' },
	{ id: 'fadein/disable', label: 'Fade In Disable' },
	{ id: 'fadein/toggle', label: 'Fade In Toggle' },
	{ id: 'fadeout/enable', label: 'Fade Out Enable' },
	{ id: 'fadeout/disable', label: 'Fade Out Disable' },
	{ id: 'fadeout/toggle', label: 'Fade Out Toggle' },
	{ id: 'crossfade/enable', label: 'Crossfade Enable' },
	{ id: 'crossfade/disable', label: 'Crossfade Disable' },
	{ id: 'crossfade/toggle', label: 'Crossfade Toggle' },
	{ id: 'resetpage/current', label: 'Reset Current Page' },
	{ id: 'resetpage/all', label: 'Reset All Pages' },
	{ id: 'group/prev', label: 'Previous Group' },
	{ id: 'group/next', label: 'Next Group' },
	{ id: 'page/prev', label: 'Previous Page' },
	{ id: 'page/next', label: 'Next Page' },
	{ id: 'soundbutton/prev', label: 'Previous Sound Button' },
	{ id: 'soundbutton/next', label: 'Next Sound Button' },
	{ id: 'lock', label: 'Lock' },
	{ id: 'automation-lock', label: 'Automation Lock' },
	{ id: 'unlock', label: 'Unlock' },
]

const PLAYER_PRESETS = [
	{ id: 'pause', name: 'Pause', command: 'pause', color: 'bg' },
	{ id: 'resume', name: 'Resume', command: 'resume', color: 'green' },
	{ id: 'stop', name: 'Stop', command: 'stop', color: 'red' },
	{ id: 'forcestop', name: 'Force Stop', command: 'forcestop', color: 'red' },
	{ id: 'playnext', name: 'Play Next', command: 'playnext', color: 'bg' },
	{ id: 'rapidfire', name: 'Rapid Fire', command: 'rapidfire', color: 'bg' },
	{ id: 'playselected', name: 'Play Selected', command: 'playselected', color: 'bg' },
	{ id: 'playselectedpause', name: 'Play Sel/Pause', command: 'playselectedpause', color: 'bg' },
	{ id: 'mute', name: 'Mute Toggle', command: 'mute', color: 'bg' },
	{ id: 'talk_enable', name: 'Talk Enable', command: 'talk/enable', color: 'bg' },
	{ id: 'talk_disable', name: 'Talk Disable', command: 'talk/disable', color: 'bg' },
	{ id: 'talk_toggle', name: 'Talk Toggle', command: 'talk/toggle', color: 'bg' },
	{ id: 'playlist_enable', name: 'Playlist Enable', command: 'playlist/enable', color: 'bg' },
	{ id: 'playlist_disable', name: 'Playlist Disable', command: 'playlist/disable', color: 'bg' },
	{ id: 'playlist_toggle', name: 'Playlist Toggle', command: 'playlist/toggle', color: 'bg' },
	{ id: 'shuffle_enable', name: 'Shuffle Enable', command: 'playlist/shuffle/enable', color: 'bg' },
	{ id: 'shuffle_disable', name: 'Shuffle Disable', command: 'playlist/shuffle/disable', color: 'bg' },
	{ id: 'shuffle_toggle', name: 'Shuffle Toggle', command: 'playlist/shuffle/toggle', color: 'bg' },
	{ id: 'multiplay_enable', name: 'Multi-play Enable', command: 'multiplay/enable', color: 'bg' },
	{ id: 'multiplay_disable', name: 'Multi-play Disable', command: 'multiplay/disable', color: 'bg' },
	{ id: 'multiplay_toggle', name: 'Multi-play Toggle', command: 'multiplay/toggle', color: 'bg' },
	{ id: 'fadein_enable', name: 'Fade In Enable', command: 'fadein/enable', color: 'bg' },
	{ id: 'fadein_disable', name: 'Fade In Disable', command: 'fadein/disable', color: 'bg' },
	{ id: 'fadein_toggle', name: 'Fade In Toggle', command: 'fadein/toggle', color: 'bg' },
	{ id: 'fadeout_enable', name: 'Fade Out Enable', command: 'fadeout/enable', color: 'bg' },
	{ id: 'fadeout_disable', name: 'Fade Out Disable', command: 'fadeout/disable', color: 'bg' },
	{ id: 'fadeout_toggle', name: 'Fade Out Toggle', command: 'fadeout/toggle', color: 'bg' },
	{ id: 'crossfade_enable', name: 'Crossfade Enable', command: 'crossfade/enable', color: 'bg' },
	{ id: 'crossfade_disable', name: 'Crossfade Disable', command: 'crossfade/disable', color: 'bg' },
	{ id: 'crossfade_toggle', name: 'Crossfade Toggle', command: 'crossfade/toggle', color: 'bg' },
	{ id: 'reset_current', name: 'Reset Current Page', command: 'resetpage/current', color: 'bg' },
	{ id: 'reset_all', name: 'Reset All Pages', command: 'resetpage/all', color: 'bg' },
	{ id: 'group_prev', name: 'Prev Group', command: 'group/prev', color: 'bg' },
	{ id: 'group_next', name: 'Next Group', command: 'group/next', color: 'bg' },
	{ id: 'page_prev', name: 'Prev Page', command: 'page/prev', color: 'bg' },
	{ id: 'page_next', name: 'Next Page', command: 'page/next', color: 'bg' },
	{ id: 'soundbutton_prev', name: 'Prev Button', command: 'soundbutton/prev', color: 'bg' },
	{ id: 'soundbutton_next', name: 'Next Button', command: 'soundbutton/next', color: 'bg' },
	{ id: 'lock', name: 'Lock', command: 'lock', color: 'red' },
	{ id: 'automation_lock', name: 'Automation Lock', command: 'automation-lock', color: 'red' },
	{ id: 'unlock', name: 'Unlock', command: 'unlock', color: 'green' },
]

class PySSPInstance extends InstanceBase {
	constructor(internal) {
		super(internal)
		this.config = {
			host: '',
			port: 5050,
			pollIntervalMs: 1500,
		}
		this.pollTimer = undefined
		this.pagesByGroup = {
			a: [{ id: 'a-1', label: 'A01' }],
		}
		this.audiosByPage = {
			'a-1': [{ id: 'a-1-1', label: 'A-1-1' }],
		}
		this.audioCatalog = []
		this.lastLibraryRefreshMs = 0
		this.libraryRefreshing = false
	}

	async init(config) {
		this.setVariableDefinitions([
			{ variableId: 'current_group', name: 'Current group' },
			{ variableId: 'current_page', name: 'Current page' },
			{ variableId: 'cue_mode', name: 'Cue mode' },
			{ variableId: 'is_playing', name: 'Is playing' },
			{ variableId: 'talk_active', name: 'Talk active' },
			{ variableId: 'playlist_enabled', name: 'Playlist enabled' },
			{ variableId: 'shuffle_enabled', name: 'Shuffle enabled' },
			{ variableId: 'multi_play_enabled', name: 'Multi-play enabled' },
			{ variableId: 'fade_in_enabled', name: 'Fade in enabled' },
			{ variableId: 'fade_out_enabled', name: 'Fade out enabled' },
			{ variableId: 'crossfade_enabled', name: 'Crossfade enabled' },
			{ variableId: 'screen_locked', name: 'Screen locked' },
			{ variableId: 'automation_locked', name: 'Automation locked' },
			{ variableId: 'playing_count', name: 'Playing track count' },
			{ variableId: 'playing_buttons', name: 'Playing button list' },
			{ variableId: 'playing_button_ids', name: 'Playing button IDs' },
			{ variableId: 'current_playing', name: 'Current playing button' },
			{ variableId: 'playing_titles', name: 'Playing titles' },
			{ variableId: 'web_remote_url', name: 'Web remote URL' },
			{ variableId: 'base_url', name: 'Configured base URL' },
			{ variableId: 'last_error', name: 'Last error' },
		])

		this.rebuildDefinitions()
		await this.applyConfig(config)
	}

	async destroy() {
		this.stopPolling()
	}

	async configUpdated(config) {
		await this.applyConfig(config)
	}

	getConfigFields() {
		return config.getConfigFields.call(this)
	}

	async applyConfig(config) {
		const host = String(config?.host || '').trim() || '127.0.0.1'

		this.config = {
			host,
			port: Number(config?.port) || 5050,
			pollIntervalMs: Math.max(500, Number(config?.pollIntervalMs) || 1500),
		}

		this.setVariableValues({
			base_url: this.getBaseUrl(),
			last_error: '',
		})

		this.startPolling()
		await this.refreshLibrary()
		await this.refreshState()
	}

	rebuildDefinitions() {
		this.setActionDefinitions(this.buildActions())
		this.setPresetDefinitions(this.buildPresets())
	}

	buildActions() {
		return {
			internal_refresh_library: {
				name: 'Internal - Refresh Presets/Lists',
				options: [],
				callback: async () => {
					await this.refreshLibrary()
					await this.refreshState()
				},
			},
			player_control: {
				name: 'Player Control',
				options: [
					{
						id: 'command',
						type: 'dropdown',
						label: 'Command',
						default: 'pause',
						choices: PLAYER_COMMAND_CHOICES,
					},
				],
				callback: async (action) => {
					const command = String(action.options.command ?? '').trim()
					if (!command) throw new Error('Command is required')
					await this.callCommand(`/api/${command}`)
				},
			},
			navigation_goto: {
				name: 'Navigation - Go To Page',
				options: this.buildGotoOptions(),
				callback: async (action) => {
					const groupUpper = String(action.options.group ?? 'A').trim().toUpperCase()
					const group = groupUpper.toLowerCase()
					const pageFieldId = this.getPageOptionId(group)
					const pageId = String(
						action.options[pageFieldId] ?? this.getPagesForGroup(group)[0]?.id ?? `${group}-1`,
					)
						.trim()
						.toLowerCase()

					if (!pageId) throw new Error('Page selection is required')
					await this.callCommand(`/api/goto/${encodeURIComponent(pageId)}`)
				},
			},
			play_audio: {
				name: 'Play Audio',
				options: this.buildPlayAudioOptions(),
				callback: async (action) => {
					const groupUpper = String(action.options.group ?? 'A').trim().toUpperCase()
					const group = groupUpper.toLowerCase()
					const pageFieldId = this.getPageOptionId(group)
					const pageId = String(
						action.options[pageFieldId] ?? this.getPagesForGroup(group)[0]?.id ?? `${group}-1`,
					)
						.trim()
						.toLowerCase()
					const audioFieldId = this.getAudioOptionId(pageId)
					const buttonId = String(
						action.options[audioFieldId] ?? this.getAudiosForPage(pageId)[0]?.id ?? `${group}-1-1`,
					)
						.trim()
						.toLowerCase()

					if (!buttonId) throw new Error('Audio selection is required')
					await this.callCommand(`/api/play/${encodeURIComponent(buttonId)}`)
				},
			},
			volume_set: {
				name: 'Volume - Set Master Level',
				options: [
					{
						id: 'level',
						type: 'number',
						label: 'Volume',
						default: 100,
						min: 0,
						max: 100,
						range: true,
					},
				],
				callback: async (action) => {
					const level = Number(action.options.level)
					if (!Number.isInteger(level) || level < 0 || level > 100) {
						throw new Error('Volume must be an integer from 0 to 100')
					}
					await this.callCommand(`/api/volume/${level}`)
				},
			},
			seek_transport: {
				name: 'Seek Transport',
				options: [
					{
						id: 'seek_mode',
						type: 'dropdown',
						label: 'Seek by',
						default: 'percent',
						choices: [
							{ id: 'percent', label: 'Percent' },
							{ id: 'time', label: 'Time String' },
						],
					},
					{
						id: 'percent',
						type: 'textinput',
						label: 'Percent',
						default: '50',
						isVisible: new Function('options', "return String(options.seek_mode ?? 'percent') === 'percent'"),
					},
					{
						id: 'time',
						type: 'textinput',
						label: 'Time',
						default: '01:00',
						isVisible: new Function('options', "return String(options.seek_mode ?? 'percent') === 'time'"),
					},
				],
				callback: async (action) => {
					const seekMode = String(action.options.seek_mode ?? 'percent').trim().toLowerCase()
					if (seekMode === 'percent') {
						const value = String(action.options.percent ?? '').trim()
						if (!value) throw new Error('Percent is required')
						await this.callCommand(`/api/seek/percent/${encodeURIComponent(value)}`)
						return
					}

					if (seekMode === 'time') {
						const value = String(action.options.time ?? '').trim()
						if (!value) throw new Error('Time is required')
						await this.callCommand(`/api/seek/time/${encodeURIComponent(value)}`)
						return
					}

					throw new Error('Seek mode must be percent or time')
				},
			},
			stage_alert: {
				name: 'Stage Alert - Send',
				options: [
					{
						id: 'text',
						type: 'textinput',
						label: 'Text',
						default: '',
					},
					{
						id: 'keep',
						type: 'checkbox',
						label: 'Keep alert visible',
						default: true,
					},
					{
						id: 'seconds',
						type: 'number',
						label: 'Seconds when not kept',
						default: 10,
						min: 1,
						max: 600,
						isVisible: new Function('options', 'return !options.keep'),
					},
				],
				callback: async (action) => {
					const text = String(action.options.text ?? '').trim()
					if (!text) throw new Error('Alert text is required')

					const keep = !!action.options.keep
					const query = new URLSearchParams({
						text,
						keep: String(keep),
					})

					if (!keep) {
						const seconds = Number(action.options.seconds)
						if (!Number.isInteger(seconds) || seconds < 1 || seconds > 600) {
							throw new Error('Seconds must be an integer from 1 to 600')
						}
						query.set('seconds', String(seconds))
					}

					await this.callCommand(`/api/alert?${query.toString()}`)
				},
			},
			clear_alert: {
				name: 'Stage Alert - Clear',
				options: [],
				callback: async () => {
					await this.callCommand('/api/alert/clear')
				},
			},
		}
	}

	buildPlayAudioOptions() {
		const options = [
			{
				id: 'group',
				type: 'dropdown',
				label: 'Group',
				default: 'A',
				choices: GROUP_CHOICES,
			},
		]

		for (const groupChoice of GROUP_CHOICES) {
			const groupUpper = String(groupChoice.id)
			const group = groupUpper.toLowerCase()
			const pages = this.getPagesForGroup(group)
			const pageFieldId = this.getPageOptionId(group)
			const defaultPageId = pages[0]?.id ?? `${group}-1`

			options.push({
				id: pageFieldId,
				type: 'dropdown',
				label: 'Page',
				default: defaultPageId,
				choices: pages,
				isVisible: this.buildGroupVisibleFn(groupUpper),
			})

			for (const pageChoice of pages) {
				const pageId = String(pageChoice.id).toLowerCase()
				const audios = this.getAudiosForPage(pageId)
				const audioFieldId = this.getAudioOptionId(pageId)
				const defaultAudioId = audios[0]?.id ?? `${pageId}-1`

				options.push({
					id: audioFieldId,
					type: 'dropdown',
					label: 'Audio',
					default: defaultAudioId,
					choices: audios.length > 0 ? audios : [{ id: defaultAudioId, label: 'No audio found' }],
					isVisible: this.buildAudioVisibleFn(groupUpper, pageFieldId, defaultPageId, pageId),
				})
			}
		}

		return options
	}

	buildGotoOptions() {
		const options = [
			{
				id: 'group',
				type: 'dropdown',
				label: 'Group',
				default: 'A',
				choices: GROUP_CHOICES,
			},
		]

		for (const groupChoice of GROUP_CHOICES) {
			const groupUpper = String(groupChoice.id)
			const group = groupUpper.toLowerCase()
			const pages = this.getPagesForGroup(group)
			const pageFieldId = this.getPageOptionId(group)
			const defaultPageId = pages[0]?.id ?? `${group}-1`

			options.push({
				id: pageFieldId,
				type: 'dropdown',
				label: 'Page',
				default: defaultPageId,
				choices: pages,
				isVisible: this.buildGroupVisibleFn(groupUpper),
			})
		}

		return options
	}

	getPageOptionId(group) {
		return `page_${String(group).toLowerCase()}`
	}

	buildGroupVisibleFn(groupUpper) {
		return new Function('options', `return String(options.group ?? 'A').toUpperCase() === '${groupUpper}'`)
	}

	buildAudioVisibleFn(groupUpper, pageFieldId, defaultPageId, pageId) {
		return new Function(
			'options',
			`if (String(options.group ?? 'A').toUpperCase() !== '${groupUpper}') return false;` +
				`const selectedPage = String(options['${pageFieldId}'] ?? '${defaultPageId}').toLowerCase();` +
				`return selectedPage === '${pageId}';`,
		)
	}

	getAudioOptionId(pageId) {
		return `audio_${String(pageId).toLowerCase().replace(/-/g, '_')}`
	}

	getPagesForGroup(group) {
		const key = String(group).toLowerCase()
		const pages = this.pagesByGroup[key]
		return pages && pages.length > 0 ? pages : [{ id: `${key}-1`, label: `${key.toUpperCase()}01` }]
	}

	getAudiosForPage(pageId) {
		const key = String(pageId).toLowerCase()
		return this.audiosByPage[key] ?? []
	}

	buildPresets() {
		const fg = combineRgb(255, 255, 255)
		const bg = combineRgb(0, 0, 0)
		const red = combineRgb(160, 0, 0)
		const green = combineRgb(0, 120, 0)
		const presets = {}
		const colors = { fg, bg, red, green }

		for (const item of PLAYER_PRESETS) {
			presets[`player_${item.id}`] = {
				type: 'button',
				category: 'Player Control',
				name: item.name,
				style: { text: item.name, size: '14', color: fg, bgcolor: colors[item.color] ?? bg },
				steps: [
					{
						down: [{ actionId: 'player_control', options: { command: item.command } }],
						up: [],
					},
				],
				feedbacks: [],
			}
		}

		presets.internal_refresh_library = {
			type: 'button',
			category: 'Internal',
			name: 'Refresh Presets/Lists',
			style: { text: 'Refresh\\nLists', size: '14', color: fg, bgcolor: bg },
			steps: [
				{
					down: [{ actionId: 'internal_refresh_library', options: {} }],
					up: [],
				},
			],
			feedbacks: [],
		}

		presets.volume_100 = {
			type: 'button',
			category: 'Volume',
			name: 'Volume 100',
			style: { text: 'Vol\\n100', size: '14', color: fg, bgcolor: bg },
			steps: [
				{
					down: [{ actionId: 'volume_set', options: { level: 100 } }],
					up: [],
				},
			],
			feedbacks: [],
		}

		presets.clear_alert = {
			type: 'button',
			category: 'Stage Alert',
			name: 'Clear Alert',
			style: { text: 'Clear\\nAlert', size: '14', color: fg, bgcolor: red },
			steps: [
				{
					down: [{ actionId: 'clear_alert', options: {} }],
					up: [],
				},
			],
			feedbacks: [],
		}

		for (const [group, pages] of Object.entries(this.pagesByGroup)) {
			const groupUpper = String(group).toUpperCase()
			const pageFieldId = this.getPageOptionId(group)
			for (const page of pages) {
				const pageId = String(page.id).toLowerCase()
				const pageLabel = String(page.label || pageId.toUpperCase())
				const presetId = `nav_${pageId.replace(/[^a-z0-9]+/g, '_')}`
				presets[presetId] = {
					type: 'button',
					category: `Navigation ${groupUpper}`,
					name: pageLabel,
					style: { text: pageLabel, size: '14', color: fg, bgcolor: bg },
					steps: [
						{
							down: [
								{
									actionId: 'navigation_goto',
									options: {
										group: groupUpper,
										[pageFieldId]: pageId,
									},
								},
							],
							up: [],
						},
					],
					feedbacks: [],
				}
			}
		}

		for (const audioItem of this.audioCatalog) {
			const groupUpper = String(audioItem.group ?? '').toUpperCase()
			const group = groupUpper.toLowerCase()
			const pageId = String(audioItem.pageId ?? '').toLowerCase()
			const buttonId = String(audioItem.buttonId ?? '').toLowerCase()
			if (!group || !pageId || !buttonId) continue

			const presetId = `play_${buttonId.replace(/[^a-z0-9]+/g, '_')}`
			const pageFieldId = this.getPageOptionId(group)
			const audioFieldId = this.getAudioOptionId(pageId)
			const buttonLabel = String(audioItem.buttonLabel || buttonId.toUpperCase())
			const title = String(audioItem.title || '').trim()

			presets[presetId] = {
				type: 'button',
				category: `${groupUpper} ${audioItem.pageLabel || pageId.toUpperCase()}`,
				name: title || buttonLabel,
				style: { text: title || buttonLabel, size: '14', color: fg, bgcolor: bg },
				steps: [
					{
						down: [
							{
								actionId: 'play_audio',
								options: {
									group: groupUpper,
									[pageFieldId]: pageId,
									[audioFieldId]: buttonId,
								},
							},
						],
						up: [],
					},
				],
				feedbacks: [],
			}
		}

		return presets
	}

	getBaseUrl() {
		return `http://${this.config.host}:${this.config.port}`
	}

	startPolling() {
		this.stopPolling()
		this.pollTimer = setInterval(() => {
			void this.refreshState()
			if (Date.now() - this.lastLibraryRefreshMs > 30000) {
				void this.refreshLibrary()
			}
		}, this.config.pollIntervalMs)
	}

	stopPolling() {
		if (this.pollTimer) {
			clearInterval(this.pollTimer)
			this.pollTimer = undefined
		}
	}

	async callCommand(path) {
		const payload = await this.requestJson(path, 'POST')
		if (payload.ok === false) {
			const message = String(payload.error?.message ?? 'Unknown pySSP error')
			throw new Error(message)
		}

		await this.refreshState()
	}

	async refreshLibrary() {
		if (this.libraryRefreshing) return
		this.libraryRefreshing = true
		try {
			const discoveredPagesByGroup = {}
			const discoveredAudiosByPage = {}
			const discoveredAudioCatalog = []

			for (const groupChoice of GROUP_CHOICES) {
				const group = String(groupChoice.id).toLowerCase()
				discoveredPagesByGroup[group] = []

				const pageGroupPayload = await this.requestJson(`/api/query/pagegroup/${group}`, 'GET')
				if (pageGroupPayload?.ok === false) continue

				const pages = Array.isArray(pageGroupPayload?.result?.pages) ? pageGroupPayload.result.pages : []
				for (const pageInfo of pages) {
					const pageNum = Number(pageInfo.page)
					if (!Number.isInteger(pageNum) || pageNum < 1) continue

					const pageId = `${group}-${pageNum}`
					const pageName = String(pageInfo.page_name ?? '').trim()
					const pageLabel = `${group.toUpperCase()}${String(pageNum).padStart(2, '0')}${pageName ? ` | ${pageName}` : ''}`
					discoveredPagesByGroup[group].push({ id: pageId, label: pageLabel })
					discoveredAudiosByPage[pageId] = []

					const pagePayload = await this.requestJson(`/api/query/page/${pageId}`, 'GET')
					if (pagePayload?.ok === false) continue

					const buttons = Array.isArray(pagePayload?.result?.buttons) ? pagePayload.result.buttons : []
					for (const buttonInfo of buttons) {
						if (!buttonInfo?.button_id) continue
						if (!buttonInfo?.assigned) continue

						const buttonId = String(buttonInfo.button_id).trim().toLowerCase()
						const title = String(buttonInfo.title ?? '').trim()
						if (!title) continue

						const buttonNum = String(buttonInfo.button ?? '').trim()
						const buttonLabel = `${buttonNum || buttonId.toUpperCase()} | ${title}`
						discoveredAudiosByPage[pageId].push({ id: buttonId, label: buttonLabel })
						discoveredAudioCatalog.push({
							group: group.toUpperCase(),
							pageId,
							pageLabel,
							buttonId,
							buttonLabel,
							title,
						})
					}
				}
			}

			const hasAnyPages = Object.values(discoveredPagesByGroup).some((entries) => entries.length > 0)
			if (hasAnyPages) {
				this.pagesByGroup = discoveredPagesByGroup
			}
			this.audiosByPage = discoveredAudiosByPage
			this.audioCatalog = discoveredAudioCatalog

			this.lastLibraryRefreshMs = Date.now()
			this.rebuildDefinitions()
		} catch (_error) {
			// Keep existing choices if metadata refresh fails.
		} finally {
			this.libraryRefreshing = false
		}
	}

	async refreshState() {
		try {
			const payload = await this.requestJson('/api/query', 'GET')
			if (payload.ok === false) {
				throw new Error(String(payload.error?.message ?? 'pySSP query failed'))
			}

			const result = payload.result ?? {}
			const playingTracks = Array.isArray(result.playing_tracks) ? result.playing_tracks : []
			const ids = playingTracks
				.map((track) => String(track.button_id ?? '').trim())
				.filter(Boolean)
			const titles = playingTracks
				.map((track) => String(track.title ?? '').trim())
				.filter(Boolean)

			this.setVariableValues({
				current_group: String(result.current_group ?? ''),
				current_page: result.current_page ?? '',
				cue_mode: !!result.cue_mode,
				is_playing: !!result.is_playing,
				talk_active: !!result.talk_active,
				playlist_enabled: !!result.playlist_enabled,
				shuffle_enabled: !!result.shuffle_enabled,
				multi_play_enabled: !!result.multi_play_enabled,
				fade_in_enabled: !!result.fade_in_enabled,
				fade_out_enabled: !!result.fade_out_enabled,
				crossfade_enabled: !!result.crossfade_enabled,
				screen_locked: !!result.screen_locked,
				automation_locked: !!result.automation_locked,
				playing_count: playingTracks.length,
				playing_buttons: Array.isArray(result.playing_buttons) ? result.playing_buttons.join(', ') : '',
				playing_button_ids: ids.join(', '),
				current_playing: String(result.current_playing ?? ''),
				playing_titles: titles.join(', '),
				web_remote_url: String(result.web_remote_url ?? ''),
				last_error: '',
			})

			this.updateStatus(InstanceStatus.Ok)
		} catch (error) {
			const message = error instanceof Error ? error.message : String(error)
			this.setVariableValues({ last_error: message })
			this.updateStatus(InstanceStatus.ConnectionFailure, message)
		}
	}

	async requestJson(path, method) {
		const controller = new AbortController()
		const timeout = setTimeout(() => controller.abort(), 4000)

		try {
			const response = await fetch(`${this.getBaseUrl()}${path}`, {
				method,
				headers: {
					Accept: 'application/json',
				},
				signal: controller.signal,
			})

			const text = await response.text()
			let body = {}

			if (text.trim()) {
				try {
					body = JSON.parse(text)
				} catch {
					throw new Error(`Invalid JSON response (${response.status})`)
				}
			}

			if (!response.ok) {
				const errMessage = String(body?.error?.message ?? `${response.status} ${response.statusText}`)
				throw new Error(errMessage)
			}

			return body
		} finally {
			clearTimeout(timeout)
		}
	}
}

runEntrypoint(PySSPInstance, [])
