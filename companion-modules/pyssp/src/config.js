import { Regex } from '@companion-module/base'

export function getConfigFields() {
	let cf = []
	cf.push(
		{
			type: 'static-text',
			id: 'info',
			width: 12,
			label: 'Information',
			value: 'Connect this module to pySSP Web Remote (Options -> Web Remote).',
		},
		{
			type: 'textinput',
			id: 'host',
			label: 'pySSP IP',
			default: '127.0.0.1',
			width: 12,
			regex: Regex.IP,
		},
		{
			type: 'number',
			id: 'port',
			label: 'Port',
			default: 5050,
			width: 12,
			min: 1,
			max: 65535,
		},
		{
			type: 'number',
			id: 'pollIntervalMs',
			label: 'Poll interval (ms)',
			default: 500,
			width: 12,
			min: 500,
			max: 30000,
		},
	)

	return cf
}
