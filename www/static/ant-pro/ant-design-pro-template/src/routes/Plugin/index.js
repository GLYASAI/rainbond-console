import React, {PureComponent} from 'react';
import {connect} from 'dva';
import {Card, Button, Icon, List} from 'antd';
import {Link, routerRedux} from 'dva/router';
import PageHeaderLayout from '../../layouts/PageHeaderLayout';
import globalUtil from '../../utils/global';
import pluginUtil from '../../utils/plugin';
import userUtil from '../../utils/user';
import TeamUtil from '../../utils/team';
import styles from './Index.less';
import Ellipsis from '../../components/Ellipsis';
import Manage from './manage';
import ConfirmModal from '../../components/ConfirmModal';
import NoPermTip from '../../components/NoPermTip';

@connect(({list, loading}) => ({}))
class PluginList extends PureComponent {
  constructor(arg) {
    super(arg);
    this.state = {
      list: [],
      deletePlugin: null
    }
    this.timer = null;
  }
  componentDidMount() {
    this.fetchPlugins();
  }
  fetchPlugins = () => {
    this
      .props
      .dispatch({
        type: 'plugin/getMyPlugins',
        payload: {
          team_name: globalUtil.getCurrTeamName()
        },
        callback: ((data) => {
          this.setState({
            list: data.list || []
          })
        })
      });
  }
  handleCreate = () => {
    this
      .props
      .dispatch(routerRedux.push(`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/create-plugin`))
  }
  hanldeDeletePlugin = () => {
    this
    .props
    .dispatch({
      type: 'plugin/deletePlugin',
      payload: {
        team_name: globalUtil.getCurrTeamName(),
        plugin_id: this.state.deletePlugin.plugin_id
      },
      callback: ((data) => {
        this.fetchPlugins();
        this.cancelDeletePlugin();
      })
    });
  }
  onDeletePlugin = (plugin) => {
     this.setState({deletePlugin: plugin})
  }
  cancelDeletePlugin = () => {
    this.setState({deletePlugin: null})
  }
  render() {
    const list = this.state.list;

    const content = (
      <div className={styles.pageHeaderContent}>
        <p>
          应用插件是标准化的为应用提供功能扩展，与应用共同运行的程序
        </p>
      </div>
    );

    const extraContent = (
      <div className={styles.extraImg}></div>
    );

    return (
      <PageHeaderLayout title="我的插件" content={content} extraContent={extraContent}>
        <div className={styles.cardList}>
          <List
            rowKey="id"
            grid={{
            gutter: 24,
            lg: 3,
            md: 2,
            sm: 1,
            xs: 1
          }}
            dataSource={[
            '', ...list
          ]}
            renderItem={item => (item
            ? (
              <List.Item
                key={item.id}
                >
                <Card
       
                  className={styles.card}
                  actions={[<Link to={`/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/myplugns/${item.plugin_id}`}>管理</Link>, <span onClick={()=>{this.onDeletePlugin(item)}}>删除</span>]}>
                  <Card.Meta
                    style={{height: 99, overflow: 'hidden'}}
                    avatar={< Icon style = {{fontSize: 50, color:'rgba(0, 0, 0, 0.2)'}}type = "api" />}
                    title={< Link to = {
                    `/team/${globalUtil.getCurrTeamName()}/region/${globalUtil.getCurrRegionName()}/myplugns/${item.plugin_id}`
                  } > {
                    item.plugin_alias
                  } < /Link>}
                    description={(
                    <Ellipsis className={styles.item} lines={3}>< p style={{ display: 'block',color:'rgb(220, 220, 220)', marginBottom:8}} > {
                      pluginUtil.getCategoryCN(item.category)
                    } < /p>{item.desc}</Ellipsis>
                  )}/>
                </Card>
              </List.Item>
            )
            : (
              <List.Item>
                <Button type="dashed" onClick={this.handleCreate} className={styles.newButton}>
                  <Icon type="plus"/>
                  新建插件
                </Button>
              </List.Item>
            ))}/>
            {this.state.deletePlugin && <ConfirmModal
          onOk={this.hanldeDeletePlugin}
          onCancel={this.cancelDeletePlugin}
          title="删除插件"
          desc="确定要删除此插件吗？"/>}
        </div>
      </PageHeaderLayout>
    );
  }
}

@connect(({user}) => ({currUser: user.currentUser}))
class Index extends PureComponent {
  render() {
    const currUser = this.props.currUser;
    const team_name = globalUtil.getCurrTeamName();
    const team = userUtil.getTeamByTeamName(currUser, team_name);
    if(!TeamUtil.canManagePlugin(team)){
       return <NoPermTip />
    }
    const pluginId = this.props.match.params.pluginId;
    if (pluginId) {
      return <Manage {...this.props}/>
    } else {
      return <PluginList {...this.props}/>
    }
  }
}

export default Index;
