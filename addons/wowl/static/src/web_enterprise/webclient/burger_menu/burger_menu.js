/** @odoo-module **/
import { useService } from '../../../core/hooks';
import { DropdownItem } from '../../../components/dropdown/dropdown_item';
import { Dropdown } from '../../../components/dropdown/dropdown';
import { BurgerUserMenu } from './user_menu/user_menu.';

/**
* This file includes the widget Menu in mobile to render the BurgerMenu which
* opens fullscreen and displays the user menu and the current app submenus.
*/
const { useListener } = require('web.custom_hooks');
//const { ComponentAdapter } = require('web.OwlCompatibility');
//const { SwitchCompanyMenuMobile } = require('web_enterprise.SwitchCompanyMenu');
//const UserMenu = require('web_enterprise.UserMenu');

// class CompanySwitcherAdapter extends ComponentAdapter {
//   constructor(parent, props) {
//     props.Component = SwitchCompanyMenuMobile;
//     super(parent, props);
//     this.switcherTitle = `
//     <div class="o_burger_menu_user_title">
//     ${this.env._t('COMPANIES')}
//     </div>`;
//   }
//   get widgetArgs() {
//     return [this.env, {title: this.switcherTitle}];
//   }
// }

class BurgerMenu extends owl.Component {
  constructor() {
    super(...arguments);
    this.user = useService('user');
    this.menuRepo = useService('menus');
    this.hm = useService('home_menu');
    this.state = owl.hooks.useState({
      isUserMenuOpened: false,
      isBurgerOpened: false,
    });
    owl.hooks.onMounted(() => {
      this.env.bus.on("HOME-MENU:TOGGLED", this, () => {
        this._closeBurger();
      });
      this.env.bus.on("ACTION_MANAGER:UPDATE", this, (req) => {
        if (req.id) {
          this._closeBurger();
        }
      });
    });
    useListener('click', 'a[data-menu]', this._closeBurger);
  }
  get currentApp() {
    return !this.hm.hasHomeMenu && this.menuRepo.getCurrentApp();
  }
  get currentAppSections() {
    return (this.currentApp && this.menuRepo.getMenuAsTree(this.currentApp.id).childrenTree) || [];
  }
  _closeBurger() {
    this.state.isUserMenuOpened = false;
    this.state.isBurgerOpened = false;
  }
  _openBurger() {
    this.state.isBurgerOpened = true;
  }
  _toggleUserMenu() {
    this.state.isUserMenuOpened = !this.state.isUserMenuOpened;
  }
  /**
   * @param {Event} ev
   */
  _onDropDownClicked(ev) {
    const dropDownToggler = ev.currentTarget.querySelector('.o_dropdown_toggler');
    const wasActive = dropDownToggler.classList.contains('o_dropdown_active');
    const toggleIcon = dropDownToggler.querySelector('.toggle_icon');
    toggleIcon.classList.toggle('fa-chevron-down', !wasActive);
    toggleIcon.classList.toggle('fa-chevron-right', wasActive);
  }
  _onMenuClicked(menu) {
    this.menuRepo.selectMenu(menu);
  }
}
BurgerMenu.template = "wowl.BurgerMenu";
BurgerMenu.components = { Portal: owl.misc.Portal, Dropdown, DropdownItem , BurgerUserMenu };

export const burgerMenu = {
  name: "wowl.burger_menu",
  Component: BurgerMenu,
  sequence: 0,
};