/******************************************************************************\

                  This file is part of the Buildbotics firmware.

         Copyright (c) 2015 - 2023, Buildbotics LLC, All rights reserved.

          This Source describes Open Hardware and is licensed under the
                                  CERN-OHL-S v2.

          You may redistribute and modify this Source and make products
     using it under the terms of the CERN-OHL-S v2 (https:/cern.ch/cern-ohl).
            This Source is distributed WITHOUT ANY EXPRESS OR IMPLIED
     WARRANTY, INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY AND FITNESS
      FOR A PARTICULAR PURPOSE. Please see the CERN-OHL-S v2 for applicable
                                   conditions.

                 Source location: https://github.com/buildbotics

       As per CERN-OHL-S v2 section 4, should You produce hardware based on
     these sources, You must maintain the Source Location clearly visible on
     the external case of the CNC Controller or other product you make using
                                   this Source.

                 For more information, email info@buildbotics.com

\******************************************************************************/


let util = require('./util')


module.exports = {
  template: '#view-debug-template',
  props: ['config', 'template', 'state'],


  data() {
    return {
      loading: false,
      path: undefined,
      editor: null,
      doc: null,
      currentLine: -1,
      breakpoints: new Set(),
      debugging: false,
      skipToLineNumber: '',
      showSkipToDialog: false
    }
  },


  computed: {
    filename() {
      return util.display_path(this.path) || '(no file selected)'
    },


    canDebug() {
      return this.path && this.state.xx == 'READY' && !this.debugging
    },


    canStep() {
      return this.debugging && this.state.debug_mode
    },


    canSkip() {
      return this.debugging && this.state.debug_mode
    },


    canContinue() {
      return this.debugging && this.state.debug_mode
    },


    currentLineNumber() {
      return this.state.debug_current_line >= 0 ? this.state.debug_current_line + 1 : 0
    }
  },


  watch: {
    'state.debug_current_line'(newLine) {
      if (newLine >= 0) {
        this.currentLine = newLine
        this.highlightCurrentLine()
      }
    },


    'state.debug_breakpoints'(newBreakpoints) {
      this.breakpoints = new Set(newBreakpoints || [])
      this.updateBreakpointGutter()
    },


    'state.debug_mode'(debugging) {
      this.debugging = debugging
      if (!debugging) {
        this.clearHighlight()
      }
    }
  },


  events: {
    'route-changing'(path, cancel) {
      if (this.debugging) {
        cancel()
        this.$root.open_dialog({
          header: 'Debug Session Active',
          body: 'Please stop the debug session before navigating away.',
          buttons: 'ok'
        })
      }
    }
  },


  attached() {
    this.initEditor()
    this.load(this.$root.selected_program.path)
    Vue.nextTick(() => {
      if (this.editor) this.editor.refresh()
    })
  },


  methods: {
    initEditor() {
      if (!this.editor && this.$els.textarea) {
        this.editor = CodeMirror.fromTextArea(this.$els.textarea, {
          lineNumbers: true,
          mode: 'gcode',
          readOnly: true,
          gutters: ['CodeMirror-linenumbers', 'debug-breakpoints', 'debug-current-line']
        })
        
        this.doc = this.editor.getDoc()
        
        // Add click handler for breakpoint gutter
        this.editor.on('gutterClick', (cm, n, gutter, e) => {
          if (gutter === 'debug-breakpoints') {
            this.toggleBreakpoint(n)
          }
        })
      }
    },


    async load(path) {
      if (this.path == path) return
      if (this.debugging) {
        await this.stopDebug()
      }
      
      this.path = path || ''
      if (!path) return

      this.loading = true

      try {
        let data = await (this.$root.select_path(path).load())

        if (this.path == path) {
          this.setContent(data)
          return true
        }

      } finally {
        if (this.path == path) this.loading = false
      }
    },


    setContent(text) {
      if (this.doc) {
        this.doc.setValue(text)
        if (this.path) {
          this.editor.setOption('mode', util.get_highlight_mode(this.path))
        }
      }
    },


    async startDebug() {
      if (!this.path) {
        this.$root.open_dialog({
          header: 'No File Selected',
          body: 'Please select a G-code file to debug.',
          buttons: 'ok'
        })
        return
      }

      try {
        await this.$api.put('debug/start/' + this.path)
        this.debugging = true
        this.$root.open_dialog({
          header: 'Debug Started',
          body: 'Debug session started. Use Step, Skip, or Continue to control execution.',
          buttons: 'ok'
        })
      } catch (error) {
        this.$root.open_dialog({
          header: 'Debug Error',
          body: `Failed to start debug session: ${error.message}`,
          buttons: 'ok'
        })
      }
    },


    async stopDebug() {
      if (!this.debugging) return

      try {
        await this.$api.put('debug/stop')
        this.debugging = false
        this.clearHighlight()
      } catch (error) {
        console.error('Failed to stop debug session:', error)
      }
    },


    async step() {
      if (!this.canStep) return

      try {
        await this.$api.put('debug/step')
      } catch (error) {
        this.$root.open_dialog({
          header: 'Debug Error',
          body: `Failed to step: ${error.message}`,
          buttons: 'ok'
        })
      }
    },


    async skip() {
      if (!this.canSkip) return

      try {
        await this.$api.put('debug/skip')
      } catch (error) {
        this.$root.open_dialog({
          header: 'Debug Error', 
          body: `Failed to skip: ${error.message}`,
          buttons: 'ok'
        })
      }
    },


    showSkipToPrompt() {
      this.skipToLineNumber = ''
      this.showSkipToDialog = true
    },


    async skipTo() {
      const lineNum = parseInt(this.skipToLineNumber)
      if (isNaN(lineNum) || lineNum < 1) {
        this.$root.open_dialog({
          header: 'Invalid Line Number',
          body: 'Please enter a valid line number.',
          buttons: 'ok'
        })
        return
      }

      try {
        await this.$api.put(`debug/skip-to/${lineNum}`)
        this.showSkipToDialog = false
      } catch (error) {
        this.$root.open_dialog({
          header: 'Debug Error',
          body: `Failed to skip to line ${lineNum}: ${error.message}`,
          buttons: 'ok'
        })
      }
    },


    async continue() {
      if (!this.canContinue) return

      try {
        await this.$api.put('debug/continue')
        this.debugging = false
        this.clearHighlight()
      } catch (error) {
        this.$root.open_dialog({
          header: 'Debug Error',
          body: `Failed to continue: ${error.message}`,
          buttons: 'ok'
        })
      }
    },


    async toggleBreakpoint(lineNumber) {
      if (!this.debugging) return

      const lineIndex = lineNumber // CodeMirror uses 0-based line numbers
      
      try {
        if (this.breakpoints.has(lineIndex)) {
          await this.$api.put(`debug/breakpoint/clear/${lineNumber + 1}`)
        } else {
          await this.$api.put(`debug/breakpoint/set/${lineNumber + 1}`)
        }
      } catch (error) {
        this.$root.open_dialog({
          header: 'Breakpoint Error',
          body: `Failed to toggle breakpoint: ${error.message}`,
          buttons: 'ok'
        })
      }
    },


    highlightCurrentLine() {
      if (!this.editor || this.currentLine < 0) return

      // Clear previous highlight
      this.clearHighlight()

      // Add current line highlight
      this.editor.addLineClass(this.currentLine, 'background', 'debug-current-line')
      
      // Scroll to current line
      this.editor.scrollIntoView({line: this.currentLine, ch: 0}, 100)
    },


    clearHighlight() {
      if (!this.editor) return

      // Clear all line highlights
      for (let i = 0; i < this.editor.lineCount(); i++) {
        this.editor.removeLineClass(i, 'background', 'debug-current-line')
      }
    },


    updateBreakpointGutter() {
      if (!this.editor) return

      // Clear all breakpoint markers
      this.editor.clearGutter('debug-breakpoints')

      // Add breakpoint markers
      for (let lineIndex of this.breakpoints) {
        const marker = document.createElement('div')
        marker.className = 'debug-breakpoint-marker'
        marker.innerHTML = '●'
        this.editor.setGutterMarker(lineIndex, 'debug-breakpoints', marker)
      }
    },


    async open() {
      let path = await this.$root.file_dialog({
        dir: this.path ? util.dirname(this.path) : '/'
      })
      if (path) this.load(path)
    },


    edit() {
      this.$root.edit(this.path)
    },


    view() {
      this.$root.view(this.path)
    }
  }
}