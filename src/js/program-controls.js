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
     the external case of the CNC Controller or other product you make using
                                   this Source.

                 For more information, email info@buildbotics.com

\******************************************************************************/


module.exports = class ProgramControls {
  constructor(api, app) {
    this.api = api
    this.app = app
    this.enabled = true
  }


  install() {
    document.addEventListener('keydown', e => this.handleKeyDown(e), true)
  }


  disable() {
    this.enabled = false
  }


  enable() {
    this.enabled = true
  }


  isInputElement(element) {
    if (!element) return false
    
    const tagName = element.tagName.toLowerCase()
    const inputTypes = ['text', 'number', 'password', 'email', 'search', 'url', 'tel']
    
    // Check for input elements
    if (tagName === 'input') {
      const type = element.type ? element.type.toLowerCase() : 'text'
      return inputTypes.includes(type)
    }
    
    // Check for textarea and contenteditable
    if (tagName === 'textarea') return true
    if (element.contentEditable === 'true') return true
    
    return false
  }


  isDialogOpen() {
    // Check if any Vue dialog component is currently shown
    // Look for .dialog-mask elements that are visible
    const dialogMasks = document.querySelectorAll('.dialog-mask')
    for (let mask of dialogMasks) {
      const computedStyle = window.getComputedStyle(mask)
      if (computedStyle.display !== 'none' && computedStyle.visibility !== 'hidden') {
        // Find the dialog container within this mask
        const container = mask.querySelector('.dialog-container')
        if (container) {
          return {
            mask: mask,
            container: container
          }
        }
      }
    }
    return null
  }


  getDialogButtons(dialogInfo) {
    if (!dialogInfo || !dialogInfo.container) return null
    
    // Look for buttons in the dialog footer
    const footer = dialogInfo.container.querySelector('.dialog-footer')
    if (!footer) return null
    
    const buttons = {}
    const buttonElements = footer.querySelectorAll('button, .pure-button, [class*="button"]')
    
    for (let element of buttonElements) {
      const text = element.textContent.toLowerCase().trim()
      // Look for continue/ok/yes type buttons
      if (text.includes('continue') || text.includes('ok') || text.includes('yes') || 
          text.includes('open') || text.includes('save') || text.includes('login') ||
          text.includes('upgrade') || text.includes('create')) {
        buttons.continue = element
      }
      // Look for cancel/no/close type buttons  
      if (text.includes('cancel') || text.includes('no') || text.includes('close') ||
          text.includes('stop')) {
        buttons.cancel = element
      }
    }
    
    return buttons
  }


  async handleKeyDown(e) {
    // Don't handle keys if disabled
    if (!this.enabled) return
    
    // Don't handle keys if user is typing in an input field
    if (this.isInputElement(e.target)) return
    
    // Don't handle keys if modifier keys are pressed (except for Escape)
    if (e.keyCode !== 27 && (e.ctrlKey || e.altKey || e.metaKey)) return
    
    const state = this.app.state
    const dialog = this.isDialogOpen()
    
    try {
      switch (e.keyCode) {
        case 27: // Escape key - Immediate E-stop
          e.preventDefault()
          e.stopPropagation()
          await this.handleEscape()
          break
          
        case 13: // Enter/Return key
          if (dialog) {
            e.preventDefault()
            e.stopPropagation()
            await this.handleDialogReturn(dialog)
          }
          break
          
        case 46: // Delete key
          e.preventDefault()
          e.stopPropagation()
          if (dialog) {
            await this.handleDialogDelete(dialog)
          } else {
            await this.handleProgramDelete(state)
          }
          break
          
        case 80: // P key
          if (!dialog) {
            e.preventDefault()
            e.stopPropagation()
            await this.handlePause(state)
          }
          break
      }
    } catch (error) {
      console.error('Error handling keyboard shortcut:', error)
    }
  }


  async handleEscape() {
    console.log('Keyboard shortcut: Escape - Triggering E-stop')
    await this.api.put('estop')
  }


  async handleDialogReturn(dialogInfo) {
    console.log('Keyboard shortcut: Return - Acting as Continue/OK in dialog')
    const buttons = this.getDialogButtons(dialogInfo)
    if (buttons && buttons.continue) {
      buttons.continue.click()
    } else {
      // If no specific continue button found, try to close messages with continue action
      await this.app.close_messages('continue')
    }
  }


  async handleDialogDelete(dialogInfo) {
    console.log('Keyboard shortcut: Delete - Acting as Cancel in dialog')
    const buttons = this.getDialogButtons(dialogInfo)
    if (buttons && buttons.cancel) {
      buttons.cancel.click()
    } else {
      // Try to close the dialog by clicking the mask (click away)
      if (dialogInfo.mask) {
        // Simulate a click away event
        const clickEvent = new MouseEvent('click', {
          bubbles: true,
          cancelable: true,
          view: window
        })
        dialogInfo.mask.dispatchEvent(clickEvent)
      }
    }
  }


  async handleProgramDelete(state) {
    if (state.xx === 'RUNNING' || state.xx === 'HOLDING' || state.xx === 'STOPPING') {
      console.log('Keyboard shortcut: Delete - Stopping program')
      await this.api.put('stop')
    }
  }


  async handlePause(state) {
    if (state.xx === 'RUNNING') {
      console.log('Keyboard shortcut: P - Pausing program')
      await this.api.put('pause')
    } else if (state.xx === 'HOLDING' || state.xx === 'STOPPING') {
      console.log('Keyboard shortcut: P - Resuming program')
      await this.api.put('unpause')
    }
  }
}